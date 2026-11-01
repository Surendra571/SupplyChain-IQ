"""SupplyChain IQ - Shortage Mitigation Recommendation Service.

End-to-end orchestration service generating feasible candidate options,
solving network-wide constrained optimization with Google OR-Tools,
ranking and comparing trade-offs, and persisting immutable mitigation records.
"""

from datetime import datetime, timezone
from decimal import Decimal
import json
import logging
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple
import uuid

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.enums import MitigationActionType, MitigationOptionStatus
from backend.app.models.planning import MitigationOption, Shortage
from backend.app.mitigation.comparison import ComparisonEngine
from backend.app.mitigation.generator import CandidateGenerator
from backend.app.mitigation.models import (
    MitigationCandidate,
    MitigationComparison,
    MitigationConfig,
    MitigationPlanSummary,
)
from backend.app.mitigation.optimizer import MitigationOptimizer

logger = logging.getLogger(__name__)


class MitigationService:
    """Enterprise mitigation recommendation and trade-off comparison service."""

    def __init__(self, data: Dict[str, List[Dict[str, Any]]], config: Optional[MitigationConfig] = None):
        self.data = data
        self.config = config or MitigationConfig()
        self.generator = CandidateGenerator(data, self.config)
        self.optimizer = MitigationOptimizer(self.config)
        self.comparison_engine = ComparisonEngine()

    def generate_mitigation_plan(
        self,
        planning_run_id: str,
        shortages: List[Any],
        current_date: Optional[datetime] = None,
    ) -> Tuple[List[MitigationComparison], List[MitigationCandidate], MitigationPlanSummary]:
        """Execute complete mitigation recommendation pipeline for all shortages.

        Returns:
            (comparisons_per_shortage, all_generated_candidates, plan_summary)
        """
        all_candidates: List[MitigationCandidate] = []
        candidates_by_shortage: Dict[str, List[MitigationCandidate]] = {}

        # 1. Generate candidate options across all 7 levers for each shortage
        for s in shortages:
            s_cands = self.generator.generate_candidates(s, current_date=current_date)
            candidates_by_shortage[s.business_id] = s_cands
            all_candidates.extend(s_cands)

        # 2. Solve constrained optimization model using Google OR-Tools
        optimized_selected, plan_summary = self.optimizer.optimize_mitigations(
            planning_run_id=planning_run_id,
            shortages=shortages,
            candidate_options=all_candidates,
        )

        # 3. Generate 4-way comparison for every shortage
        comparisons: List[MitigationComparison] = []
        for s in shortages:
            s_cands = candidates_by_shortage.get(s.business_id, [])
            comp = self.comparison_engine.compare_options(
                shortage=s,
                all_candidates=s_cands,
                optimized_selected_candidates=optimized_selected,
            )
            comparisons.append(comp)

        return comparisons, all_candidates, plan_summary

    def export_mitigation_snapshots(
        self,
        output_dir: Path,
        comparisons: List[MitigationComparison],
        candidates: List[MitigationCandidate],
        summary: MitigationPlanSummary,
    ) -> Path:
        """Persist immutable mitigation recommendations to CSV and JSON snapshot files."""
        output_dir.mkdir(parents=True, exist_ok=True)

        # 1. All Candidates CSV
        cands_dicts = [c.model_dump() for c in candidates]
        df_cands = pd.DataFrame(cands_dicts)
        df_cands.to_csv(output_dir / "mitigation_candidates.csv", index=False)

        # 2. Recommended / Optimized Options CSV
        rec_options = [c for c in candidates if c.is_feasible and c.rank == 1]
        df_rec = pd.DataFrame([r.model_dump() for r in rec_options])
        df_rec.to_csv(output_dir / "recommended_mitigations.csv", index=False)

        # 3. Comparisons JSON
        comps_dicts = [comp.model_dump() for comp in comparisons]
        with open(output_dir / "mitigation_comparisons.json", "w", encoding="utf-8") as f:
            json.dump(comps_dicts, f, indent=2)

        # 4. Summary JSON
        with open(output_dir / "mitigation_summary.json", "w", encoding="utf-8") as f:
            json.dump(summary.model_dump(), f, indent=2)

        return output_dir

    async def persist_to_database(
        self,
        session: AsyncSession,
        comparisons: List[MitigationComparison],
    ) -> int:
        """Persist ranked mitigation options into PostgreSQL mitigation_options table."""
        # Query existing shortages to map business_id to UUID
        stmt = select(Shortage.id, Shortage.business_id)
        result = await session.execute(stmt)
        shortage_uuid_map = {row.business_id: row.id for row in result.all()}

        option_records = []
        for comp in comparisons:
            s_uuid = shortage_uuid_map.get(comp.shortage_id)
            if not s_uuid:
                continue

            for cand in comp.all_options:
                opt_rec = MitigationOption(
                    id=uuid.uuid4(),
                    business_id=f"MIT-{cand.candidate_id}",
                    shortage_id=s_uuid,
                    action_type=cand.action_type,
                    status=cand.status,
                    recommended_qty=max(1, cand.recoverable_quantity),
                    source_reference_id=cand.source_reference_id,
                    incremental_cost=Decimal(str(cand.total_cost)),
                    service_gain_score=Decimal(str(cand.service_level_impact)),
                    roi_ratio=Decimal(str(cand.roi_ratio)),
                    rank=cand.rank,
                    details_json=json.dumps({
                        "is_feasible": cand.is_feasible,
                        "infeasibility_reasons": cand.infeasibility_reasons,
                        "expected_arrival_date": cand.expected_arrival_date,
                        "expected_arrival_week": cand.expected_arrival_week,
                        "recovery_time_days": cand.recovery_time_days,
                        "quantity_still_at_risk": cand.quantity_still_at_risk,
                        "procurement_cost": cand.additional_procurement_cost,
                        "transportation_cost": cand.transportation_cost,
                        "production_cost": cand.production_cost,
                        "explanation": cand.explanation,
                    }),
                )
                option_records.append(opt_rec)

        batch_size = 1000
        for i in range(0, len(option_records), batch_size):
            session.add_all(option_records[i : i + batch_size])
            await session.flush()

        inserted_count = len(option_records)
        await session.commit()
        return inserted_count


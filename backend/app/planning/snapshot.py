"""SupplyChain IQ - Planning Run Snapshot Manager & Persistence Engine."""

from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

import pandas as pd
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.enums import PlanningRunStatus, ShortageSeverity, ShortageStatus
from backend.app.models.planning import PlanningRun, Shortage
from backend.app.planning.models import PlanningRunSummary, ShortageOutput, WeeklyProjection


class PlanningSnapshotManager:
    """Manages immutable persistence of planning runs and weekly balance projections.

    Satisfies Rule 9: Track all changes through planning-run snapshots.
    """

    def __init__(self, export_base_dir: Optional[Path] = None):
        self.export_base_dir = export_base_dir or Path("data/planning_runs")

    def export_snapshot_files(
        self,
        summary: PlanningRunSummary,
        projections: List[WeeklyProjection],
        shortages: List[ShortageOutput],
        custom_dir: Optional[Path] = None,
    ) -> Path:
        """Persist planning outputs to immutable directory snapshot files."""
        run_dir = custom_dir or (self.export_base_dir / f"run_{summary.run_number:04d}")
        run_dir.mkdir(parents=True, exist_ok=True)

        # 1. Summary JSON
        summary_file = run_dir / "summary.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary.model_dump(), f, indent=2)

        # 2. Projections CSV
        proj_dicts = [p.model_dump() for p in projections]
        proj_df = pd.DataFrame(proj_dicts)
        proj_file = run_dir / "projections.csv"
        proj_df.to_csv(proj_file, index=False)

        # 3. Shortages CSV & JSON
        short_dicts = [s.model_dump() for s in shortages]
        short_df = pd.DataFrame(short_dicts)
        short_file = run_dir / "shortages.csv"
        short_df.to_csv(short_file, index=False)

        short_json_file = run_dir / "shortages.json"
        with open(short_json_file, "w", encoding="utf-8") as f:
            json.dump(short_dicts, f, indent=2)

        return run_dir

    async def persist_to_database(
        self,
        session: AsyncSession,
        summary: PlanningRunSummary,
        shortages: List[ShortageOutput],
    ) -> uuid.UUID:
        """Persist planning run header and detected shortages to PostgreSQL."""
        # 1. Mark existing non-superseded runs as superseded
        await session.execute(
            update(PlanningRun)
            .where(PlanningRun.is_superseded == False)
            .values(is_superseded=True)
        )

        # 2. Create PlanningRun header
        run_uuid = uuid.uuid4()
        run_record = PlanningRun(
            id=run_uuid,
            business_id=f"RUN-{summary.run_number:04d}",
            run_number=summary.run_number,
            status=PlanningRunStatus.COMPLETED,
            horizon_weeks=summary.horizon_weeks,
            started_at=datetime.fromisoformat(summary.started_at),
            completed_at=datetime.fromisoformat(summary.completed_at),
            config_json=json.dumps(summary.config),
            summary_json=json.dumps(summary.model_dump()),
            is_superseded=False,
        )
        session.add(run_record)

        # 3. High-Performance Chunked Batch Insertion of Shortage records
        shortage_records = []
        for s in shortages:
            shortage_rec = Shortage(
                id=uuid.uuid4(),
                business_id=s.business_id,
                planning_run_id=run_uuid,
                sku_id=uuid.UUID(s.sku_id),
                location_id=uuid.UUID(s.location_id),
                week_bucket=s.week_bucket,
                projected_deficit_qty=s.projected_deficit_qty,
                demand_shortage_qty=s.demand_shortage_qty,
                safety_stock_gap_qty=s.safety_stock_gap_qty,
                severity=s.severity,
                priority_tier=s.priority_tier.value,
                priority_score=Decimal(str(s.priority_score)),
                financial_impact=Decimal(str(s.financial_impact)),
                root_cause=s.root_cause.value,
                root_cause_explanation=s.root_cause_explanation,
                details_json=json.dumps(s.details),
                status=ShortageStatus.DETECTED,
            )
            shortage_records.append(shortage_rec)

        batch_size = 1000
        for i in range(0, len(shortage_records), batch_size):
            session.add_all(shortage_records[i : i + batch_size])
            await session.flush()

        await session.commit()
        return run_uuid


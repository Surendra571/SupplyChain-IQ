"""SupplyChain IQ - Mitigation Query Service."""

import json
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import EntityNotFoundError
from backend.app.models.planning import MitigationOption
from backend.app.repositories.planning_repo import PlanningRepository
from backend.app.schemas.decision_api import MitigationComparisonView, MitigationOptionItem


class MitigationQueryService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = PlanningRepository(session)

    async def get_shortage_mitigations(self, shortage_id: str) -> MitigationComparisonView:
        shortage_item = await self.repo.get_shortage(shortage_id)
        if not shortage_item:
            raise EntityNotFoundError("Shortage", shortage_id)
        shortage, sku, loc = shortage_item

        options = await self.repo.get_mitigations_for_shortage(shortage.id)

        candidate_items: List[MitigationOptionItem] = []
        cheapest = None
        fastest = None
        best_service = None
        recommended = None

        for opt in options:
            details_dict = json.loads(opt.details_json) if opt.details_json else {}
            item = MitigationOptionItem(
                id=opt.id,
                business_id=opt.business_id,
                shortage_id=opt.shortage_id,
                action_type=opt.action_type,
                status=opt.status,
                recommended_qty=opt.recommended_qty,
                source_reference_id=opt.source_reference_id,
                incremental_cost=opt.incremental_cost,
                service_gain_score=opt.service_gain_score,
                roi_ratio=opt.roi_ratio,
                rank=opt.rank,
                details=details_dict,
                created_at=opt.created_at,
            )
            candidate_items.append(item)

            if opt.rank == 1:
                action_str = opt.action_type.value if hasattr(opt.action_type, "value") else str(opt.action_type)
                recommended = {
                    "id": str(opt.id),
                    "action_type": action_str,
                    "recommended_qty": opt.recommended_qty,
                    "cost": float(opt.incremental_cost),
                    "roi": float(opt.roi_ratio),
                    "details": details_dict,
                }

        # Derive cheapest, fastest, and best service from candidates
        if candidate_items:
            cheapest_opt = min(candidate_items, key=lambda c: c.incremental_cost)
            ch_action_str = cheapest_opt.action_type.value if hasattr(cheapest_opt.action_type, "value") else str(cheapest_opt.action_type)
            cheapest = {
                "id": str(cheapest_opt.id),
                "action_type": ch_action_str,
                "cost": float(cheapest_opt.incremental_cost),
                "recommended_qty": cheapest_opt.recommended_qty,
            }

            best_serv_opt = max(candidate_items, key=lambda c: c.service_gain_score)
            bs_action_str = best_serv_opt.action_type.value if hasattr(best_serv_opt.action_type, "value") else str(best_serv_opt.action_type)
            best_service = {
                "id": str(best_serv_opt.id),
                "action_type": bs_action_str,
                "service_score": float(best_serv_opt.service_gain_score),
                "recommended_qty": best_serv_opt.recommended_qty,
            }

            fastest = recommended  # Best available expedited turnaround

        summary_text = (
            f"Evaluated {len(candidate_items)} mitigation option(s) for {shortage.projected_deficit_qty} unit deficit. "
            f"Recommended strategy: {recommended['action_type'] if recommended else 'No feasible action'}."
        )

        return MitigationComparisonView(
            shortage_id=shortage.business_id,
            sku_code=sku.sku_code,
            location_code=loc.location_code,
            week_bucket=shortage.week_bucket,
            projected_deficit_qty=shortage.projected_deficit_qty,
            cheapest_option=cheapest,
            fastest_option=fastest,
            best_service_option=best_service,
            recommended_option=recommended,
            all_candidates=candidate_items,
            comparison_summary=summary_text,
        )

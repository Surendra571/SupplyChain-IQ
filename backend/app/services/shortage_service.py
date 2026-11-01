"""SupplyChain IQ - Shortage Workbench Service."""

from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import EntityNotFoundError
from backend.app.models.master_data import Location, SKU
from backend.app.models.planning import MitigationOption, Shortage
from backend.app.repositories.planning_repo import PlanningRepository
from backend.app.schemas.common import PaginatedResponse, PaginationParams
from backend.app.schemas.planning_api import ShortageEnrichedResponse, ShortageFilterParams


class ShortageService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = PlanningRepository(session)

    async def list_shortages(
        self,
        filters: ShortageFilterParams,
        pagination: PaginationParams,
    ) -> PaginatedResponse[ShortageEnrichedResponse]:
        rows, total = await self.repo.list_shortages(
            filters=filters,
            page=pagination.page,
            page_size=pagination.page_size,
            sort_by=pagination.sort_by,
            sort_dir=pagination.sort_dir,
        )

        items: List[ShortageEnrichedResponse] = []
        for s, sku, loc, rec_opt in rows:
            rec_action = (
                rec_opt.action_type.value if hasattr(rec_opt.action_type, "value") else str(rec_opt.action_type)
            ) if rec_opt else None
            loc_type_str = loc.location_type.value if hasattr(loc.location_type, "value") else str(loc.location_type)
            items.append(
                ShortageEnrichedResponse(
                    id=s.id,
                    business_id=s.business_id,
                    planning_run_id=s.planning_run_id,
                    sku_id=sku.id,
                    sku_code=sku.sku_code,
                    sku_name=sku.name,
                    unit_of_measure=sku.unit_of_measure,
                    location_id=loc.id,
                    location_code=loc.location_code,
                    location_name=loc.name,
                    location_type=loc_type_str,
                    week_bucket=s.week_bucket,
                    projected_deficit_qty=s.projected_deficit_qty,
                    demand_shortage_qty=s.demand_shortage_qty,
                    safety_stock_gap_qty=s.safety_stock_gap_qty,
                    severity=s.severity,
                    priority_tier=s.priority_tier,
                    priority_score=s.priority_score,
                    financial_impact=s.financial_impact,
                    root_cause=s.root_cause,
                    root_cause_explanation=s.root_cause_explanation,
                    status=s.status,
                    has_mitigation=rec_opt is not None,
                    recommended_action=rec_action,
                    created_at=s.created_at,
                )
            )

        total_pages = (total + pagination.page_size - 1) // pagination.page_size if total > 0 else 0

        return PaginatedResponse[ShortageEnrichedResponse](
            items=items,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
            total_pages=total_pages,
        )

    async def get_shortage(self, identifier: str) -> ShortageEnrichedResponse:
        item = await self.repo.get_shortage(identifier)
        if not item:
            raise EntityNotFoundError("Shortage", identifier)
        s, sku, loc = item
        mitigations = await self.repo.get_mitigations_for_shortage(s.id)
        rec_opt = mitigations[0] if mitigations else None

        rec_action = (
            rec_opt.action_type.value if hasattr(rec_opt.action_type, "value") else str(rec_opt.action_type)
        ) if rec_opt else None
        loc_type_str = loc.location_type.value if hasattr(loc.location_type, "value") else str(loc.location_type)

        return ShortageEnrichedResponse(
            id=s.id,
            business_id=s.business_id,
            planning_run_id=s.planning_run_id,
            sku_id=sku.id,
            sku_code=sku.sku_code,
            sku_name=sku.name,
            unit_of_measure=sku.unit_of_measure,
            location_id=loc.id,
            location_code=loc.location_code,
            location_name=loc.name,
            location_type=loc_type_str,
            week_bucket=s.week_bucket,
            projected_deficit_qty=s.projected_deficit_qty,
            demand_shortage_qty=s.demand_shortage_qty,
            safety_stock_gap_qty=s.safety_stock_gap_qty,
            severity=s.severity,
            priority_tier=s.priority_tier,
            priority_score=s.priority_score,
            financial_impact=s.financial_impact,
            root_cause=s.root_cause,
            root_cause_explanation=s.root_cause_explanation,
            status=s.status,
            has_mitigation=rec_opt is not None,
            recommended_action=rec_action,
            created_at=s.created_at,
        )

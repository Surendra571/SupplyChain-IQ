"""SupplyChain IQ - Planning & Shortage Repository Layer."""

import json
from typing import Any, Dict, List, Optional, Tuple
import uuid
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models.master_data import Location, SKU
from backend.app.models.planning import MitigationOption, PlanningRun, Shortage
from backend.app.repositories.base import BaseRepository
from backend.app.schemas.planning_api import ShortageFilterParams


class PlanningRepository(BaseRepository[PlanningRun]):
    def __init__(self, session: AsyncSession):
        super().__init__(PlanningRun, session)

    async def get_latest_run(self) -> Optional[PlanningRun]:
        stmt = (
            select(PlanningRun)
            .order_by(desc(PlanningRun.run_number))
            .limit(1)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_run(self, identifier: str) -> Optional[PlanningRun]:
        try:
            val_uuid = uuid.UUID(identifier)
            stmt = select(PlanningRun).where(PlanningRun.id == val_uuid)
        except ValueError:
            stmt = select(PlanningRun).where(PlanningRun.business_id == identifier)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_runs(
        self,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[PlanningRun], int]:
        stmt = select(PlanningRun).order_by(desc(PlanningRun.run_number))
        return await self.list_paginated(stmt, page=page, page_size=page_size)

    async def list_shortages(
        self,
        filters: ShortageFilterParams,
        page: int = 1,
        page_size: int = 50,
        sort_by: Optional[str] = None,
        sort_dir: Optional[str] = "desc",
    ) -> Tuple[List[Tuple[Shortage, SKU, Location, Optional[MitigationOption]]], int]:
        """Query shortages joined with SKU, Location, and recommended MitigationOption."""
        # Join Shortage -> SKU and Location
        stmt = (
            select(Shortage, SKU, Location)
            .join(SKU, Shortage.sku_id == SKU.id)
            .join(Location, Shortage.location_id == Location.id)
        )

        # Apply Filters
        if filters.planning_run_id:
            try:
                run_uuid = uuid.UUID(filters.planning_run_id)
                stmt = stmt.where(Shortage.planning_run_id == run_uuid)
            except ValueError:
                # Match via business_id on PlanningRun
                stmt = stmt.join(PlanningRun, Shortage.planning_run_id == PlanningRun.id).where(
                    PlanningRun.business_id == filters.planning_run_id
                )

        if filters.severity:
            stmt = stmt.where(Shortage.severity == filters.severity)
        if filters.priority_tier:
            stmt = stmt.where(Shortage.priority_tier == filters.priority_tier)
        if filters.status:
            stmt = stmt.where(Shortage.status == filters.status)
        if filters.sku_code:
            stmt = stmt.where(SKU.sku_code.ilike(f"%{filters.sku_code}%"))
        if filters.location_code:
            stmt = stmt.where(Location.location_code.ilike(f"%{filters.location_code}%"))
        if filters.week_bucket:
            stmt = stmt.where(Shortage.week_bucket == filters.week_bucket)
        if filters.root_cause:
            stmt = stmt.where(Shortage.root_cause == filters.root_cause)
        if filters.min_priority_score is not None:
            stmt = stmt.where(Shortage.priority_score >= filters.min_priority_score)
        if filters.max_priority_score is not None:
            stmt = stmt.where(Shortage.priority_score <= filters.max_priority_score)

        # Count total matching
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_res = await self.session.execute(count_stmt)
        total = count_res.scalar_one() or 0

        # Sorting
        order_col = Shortage.priority_score
        if sort_by == "projected_deficit_qty":
            order_col = Shortage.projected_deficit_qty
        elif sort_by == "week_bucket":
            order_col = Shortage.week_bucket
        elif sort_by == "financial_impact":
            order_col = Shortage.financial_impact
        elif sort_by == "sku_code":
            order_col = SKU.sku_code
        elif sort_by == "location_code":
            order_col = Location.location_code

        if sort_dir and sort_dir.lower() == "asc":
            stmt = stmt.order_by(order_col.asc())
        else:
            stmt = stmt.order_by(order_col.desc())

        # Pagination
        offset_val = (page - 1) * page_size
        stmt = stmt.limit(page_size).offset(offset_val)

        res = await self.session.execute(stmt)
        rows = res.all()

        results = []
        shortage_ids = [r[0].id for r in rows]
        # Fetch rank 1 recommended options in batch
        rec_options_map: Dict[uuid.UUID, MitigationOption] = {}
        if shortage_ids:
            rec_stmt = (
                select(MitigationOption)
                .where(MitigationOption.shortage_id.in_(shortage_ids))
                .where(MitigationOption.rank == 1)
            )
            rec_res = await self.session.execute(rec_stmt)
            for opt in rec_res.scalars().all():
                rec_options_map[opt.shortage_id] = opt

        for s, sku, loc in rows:
            rec_opt = rec_options_map.get(s.id)
            results.append((s, sku, loc, rec_opt))

        return results, total

    async def get_shortage(self, identifier: str) -> Optional[Tuple[Shortage, SKU, Location]]:
        stmt = (
            select(Shortage, SKU, Location)
            .join(SKU, Shortage.sku_id == SKU.id)
            .join(Location, Shortage.location_id == Location.id)
        )
        try:
            val_uuid = uuid.UUID(identifier)
            stmt = stmt.where(Shortage.id == val_uuid)
        except ValueError:
            stmt = stmt.where(Shortage.business_id == identifier)

        res = await self.session.execute(stmt)
        row = res.first()
        return (row[0], row[1], row[2]) if row else None

    async def get_mitigations_for_shortage(self, shortage_id: uuid.UUID) -> List[MitigationOption]:
        stmt = (
            select(MitigationOption)
            .where(MitigationOption.shortage_id == shortage_id)
            .order_by(MitigationOption.rank.asc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_mitigation_option(self, identifier: str) -> Optional[MitigationOption]:
        try:
            val_uuid = uuid.UUID(identifier)
            stmt = select(MitigationOption).where(MitigationOption.id == val_uuid)
        except ValueError:
            stmt = select(MitigationOption).where(MitigationOption.business_id == identifier)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()


"""SupplyChain IQ - Master Data Repository."""

from typing import List, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.master_data import Location, SKU, Supplier
from backend.app.repositories.base import BaseRepository


class MasterDataRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_skus(
        self,
        sku_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 100,
    ) -> Tuple[List[SKU], int]:
        repo = BaseRepository(SKU, self.session)
        stmt = select(SKU)
        if sku_type:
            stmt = stmt.where(SKU.sku_type == sku_type)
        stmt = stmt.order_by(SKU.sku_code.asc())
        return await repo.list_paginated(stmt, page=page, page_size=page_size)

    async def list_locations(
        self,
        location_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 100,
    ) -> Tuple[List[Location], int]:
        repo = BaseRepository(Location, self.session)
        stmt = select(Location)
        if location_type:
            stmt = stmt.where(Location.location_type == location_type)
        stmt = stmt.order_by(Location.location_code.asc())
        return await repo.list_paginated(stmt, page=page, page_size=page_size)

    async def list_suppliers(
        self,
        page: int = 1,
        page_size: int = 100,
    ) -> Tuple[List[Supplier], int]:
        repo = BaseRepository(Supplier, self.session)
        stmt = select(Supplier).order_by(Supplier.supplier_code.asc())
        return await repo.list_paginated(stmt, page=page, page_size=page_size)


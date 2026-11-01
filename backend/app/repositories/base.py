"""SupplyChain IQ - Base Async Repository."""

from typing import Any, Generic, List, Optional, Tuple, Type, TypeVar
import uuid
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Generic asynchronous repository using SQLAlchemy 2.0 select constructs."""

    def __init__(self, model: Type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def get_by_id(self, entity_id: uuid.UUID) -> Optional[ModelType]:
        stmt = select(self.model).where(self.model.id == entity_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_business_id(self, business_id: str) -> Optional[ModelType]:
        stmt = select(self.model).where(self.model.business_id == business_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_paginated(
        self,
        stmt_query,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[ModelType], int]:
        """Execute a paginated query returning (items, total_count)."""
        # Count total
        count_stmt = select(func.count()).select_from(stmt_query.order_by(None).subquery())
        count_res = await self.session.execute(count_stmt)
        total = count_res.scalar_one() or 0

        # Fetch page slice
        offset_val = (page - 1) * page_size
        paged_stmt = stmt_query.limit(page_size).offset(offset_val)
        result = await self.session.execute(paged_stmt)
        items = list(result.scalars().all())

        return items, total


"""SupplyChain IQ - Audit Repository."""

from typing import List, Optional, Tuple
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.audit import AuditEvent
from backend.app.repositories.base import BaseRepository


class AuditRepository(BaseRepository[AuditEvent]):
    def __init__(self, session: AsyncSession):
        super().__init__(AuditEvent, session)

    async def list_events(
        self,
        entity_name: Optional[str] = None,
        entity_id: Optional[str] = None,
        action: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[AuditEvent], int]:
        stmt = select(AuditEvent)
        if entity_name:
            stmt = stmt.where(AuditEvent.entity_name == entity_name)
        if entity_id:
            stmt = stmt.where(AuditEvent.entity_id == entity_id)
        if action:
            stmt = stmt.where(AuditEvent.action == action)

        stmt = stmt.order_by(desc(AuditEvent.created_at))
        return await self.list_paginated(stmt, page=page, page_size=page_size)


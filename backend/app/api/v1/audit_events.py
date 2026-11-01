"""SupplyChain IQ - Audit Events Router."""

from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_async_session, require_roles
from backend.app.core.rbac import UserRole
from backend.app.repositories.audit_repo import AuditRepository
from backend.app.schemas.audit import AuditEventResponse
from backend.app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/audit-events", tags=["Audit Trail & Governance"])


@router.get("", response_model=PaginatedResponse[AuditEventResponse], summary="Query Immutable Audit Trail")
async def list_audit_events(
    current_user: Annotated[
        dict,
        Depends(require_roles([UserRole.OPERATIONS_MANAGER, UserRole.ADMINISTRATOR, UserRole.PLANNER])),
    ],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    entity_name: Optional[str] = Query(default=None, description="Filter by entity name e.g. MitigationDecision"),
    entity_id: Optional[str] = Query(default=None, description="Filter by entity business ID"),
    action: Optional[str] = Query(default=None, description="APPROVED, REJECTED, CREATE, etc."),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
):
    """Retrieve immutable chronological audit records logging every state change."""
    repo = AuditRepository(session)
    events, total = await repo.list_events(
        entity_name=entity_name,
        entity_id=entity_id,
        action=action,
        page=page,
        page_size=page_size,
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return PaginatedResponse[AuditEventResponse](
        items=[AuditEventResponse.model_validate(e) for e in events],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


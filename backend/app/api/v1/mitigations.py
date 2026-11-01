"""SupplyChain IQ - Mitigations Router."""

from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_async_session, get_current_user
from backend.app.schemas.decision_api import MitigationComparisonView
from backend.app.services.mitigation_service import MitigationQueryService

router = APIRouter(prefix="/mitigations", tags=["Mitigation Recommendations & Trade-offs"])


@router.get("/shortage/{shortage_id}", response_model=MitigationComparisonView, summary="Get Mitigation Trade-offs for Shortage")
async def get_mitigations_for_shortage(
    shortage_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Retrieve 4-way trade-off analysis (Cheapest, Fastest, Best Service, Recommended) and all candidate options."""
    service = MitigationQueryService(session)
    return await service.get_shortage_mitigations(shortage_id)


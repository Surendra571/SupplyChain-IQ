"""SupplyChain IQ - Mitigation Decisions Router."""

from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_async_session, get_current_user, get_idempotency_key
from backend.app.core.exceptions import EntityNotFoundError
from backend.app.repositories.decision_repo import DecisionRepository
from backend.app.schemas.decision_api import DecisionSubmitRequest, DecisionSubmitResponse
from backend.app.services.decision_service import DecisionService

router = APIRouter(prefix="/decisions", tags=["Mitigation Decisions & Approvals"])


@router.post(
    "",
    response_model=DecisionSubmitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Planner Mitigation Decision",
)
async def submit_decision(
    payload: DecisionSubmitRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    idempotency_key: Annotated[Optional[str], Depends(get_idempotency_key)],
):
    """Submit an official planner decision (APPROVE, REJECT, OVERRIDE) with idempotency and audit enforcement."""
    service = DecisionService(session)
    return await service.submit_decision(
        request=payload,
        user_id=current_user["user_id"],
        user_role=current_user["role"],
        idempotency_key=idempotency_key,
    )


@router.get("/{decision_id}", response_model=DecisionSubmitResponse, summary="Get Decision Record")
async def get_decision(
    decision_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Fetch an immutable historical mitigation decision record."""
    repo = DecisionRepository(session)
    dec = await repo.get_decision_by_id(decision_id)
    if not dec:
        raise EntityNotFoundError("MitigationDecision", decision_id)

    return DecisionSubmitResponse(
        id=dec.id,
        business_id=dec.business_id,
        mitigation_option_id=dec.mitigation_option_id,
        planner_id=dec.planner_id,
        decision=dec.decision,
        override_qty=dec.override_qty,
        reason=dec.reason,
        decided_at=dec.decided_at,
        status="REGISTERED",
        message="Decision retrieved.",
    )


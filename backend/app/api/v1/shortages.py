"""SupplyChain IQ - Shortage Workbench Router."""

from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_async_session, get_current_user
from backend.app.models.enums import ShortageSeverity, ShortageStatus
from backend.app.schemas.common import PaginatedResponse, PaginationParams
from backend.app.schemas.planning_api import ShortageEnrichedResponse, ShortageFilterParams, ShortagePABDetailResponse
from backend.app.services.planning_service import PlanningService
from backend.app.services.shortage_service import ShortageService

router = APIRouter(prefix="/shortages", tags=["Shortage Workbench"])


@router.get("", response_model=PaginatedResponse[ShortageEnrichedResponse], summary="Query Projected Shortages")
async def list_shortages(
    current_user: Annotated[dict, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    planning_run_id: Optional[str] = Query(default=None, description="Filter by planning run UUID or business ID"),
    severity: Optional[ShortageSeverity] = Query(default=None, description="CRITICAL (PAB < 0) or WARNING (Safety Stock Gap)"),
    priority_tier: Optional[str] = Query(default=None, description="Critical, High, Medium, Low"),
    status: Optional[ShortageStatus] = Query(default=None, description="DETECTED, ACKNOWLEDGED, MITIGATED, RESOLVED"),
    sku_code: Optional[str] = Query(default=None, description="SKU code search pattern"),
    location_code: Optional[str] = Query(default=None, description="Location code search pattern"),
    week_bucket: Optional[str] = Query(default=None, description="Target ISO week e.g. 2026W03"),
    root_cause: Optional[str] = Query(default=None, description="Shortage root cause diagnostic"),
    min_priority_score: Optional[float] = Query(default=None, ge=0.0, le=100.0),
    max_priority_score: Optional[float] = Query(default=None, ge=0.0, le=100.0),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    sort_by: Optional[str] = Query(default="priority_score", description="priority_score, projected_deficit_qty, week_bucket, financial_impact"),
    sort_dir: Optional[str] = Query(default="desc", description="asc or desc"),
):
    """Query prioritized shortage workbench records with multi-dimensional filtering, sorting, and pagination."""
    filters = ShortageFilterParams(
        planning_run_id=planning_run_id,
        severity=severity,
        priority_tier=priority_tier,
        status=status,
        sku_code=sku_code,
        location_code=location_code,
        week_bucket=week_bucket,
        root_cause=root_cause,
        min_priority_score=min_priority_score,
        max_priority_score=max_priority_score,
    )
    pagination = PaginationParams(
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )

    service = ShortageService(session)
    return await service.list_shortages(filters, pagination)


@router.get("/{shortage_id}", response_model=ShortageEnrichedResponse, summary="Get Shortage Detail")
async def get_shortage_detail(
    shortage_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Retrieve full detail, priority scores, and root-cause diagnostic for a single shortage."""
    service = ShortageService(session)
    return await service.get_shortage(shortage_id)


@router.get("/{shortage_id}/pab", response_model=ShortagePABDetailResponse, summary="Get Time-Phased PAB Curve")
async def get_shortage_pab_curve(
    shortage_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Fetch time-series weekly inventory balance projection (PAB, demand, receipts, safety stock) for charts."""
    service = PlanningService(session)
    return await service.get_shortage_pab(shortage_id)


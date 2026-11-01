"""SupplyChain IQ - Planning Runs Router."""

from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_async_session, get_current_user, get_idempotency_key, require_roles
from backend.app.core.idempotency import idempotency_store
from backend.app.core.rbac import UserRole
from backend.app.repositories.planning_repo import PlanningRepository
from backend.app.schemas.common import PaginatedResponse
from backend.app.schemas.planning import PlanningRunResponse
from backend.app.schemas.planning_api import PlanningRunDetailResponse, PlanningRunTriggerRequest
from backend.app.services.planning_service import PlanningService

router = APIRouter(prefix="/planning-runs", tags=["Planning Runs & Orchestration"])


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger Weekly Planning & Optimization Run",
)
async def trigger_planning_run(
    payload: PlanningRunTriggerRequest,
    current_user: Annotated[
        dict,
        Depends(require_roles([UserRole.PLANNER, UserRole.OPERATIONS_MANAGER, UserRole.ADMINISTRATOR])),
    ],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    idempotency_key: Annotated[Optional[str], Depends(get_idempotency_key)],
    use_celery: bool = Query(default=False, description="Queue as background Celery job if Redis is available"),
):
    """Trigger time-phased balance MRP simulation and constrained OR-Tools mitigation optimization."""
    # Check Idempotency Key
    if idempotency_key:
        is_new, record = idempotency_store.start_operation(idempotency_key)
        if not is_new and record.status == "COMPLETED" and record.response_body:
            return record.response_body

    service = PlanningService(session)
    result = await service.trigger_run(
        horizon_weeks=payload.horizon_weeks,
        data_dir=payload.data_dir,
        persist_db=payload.persist_db,
        use_celery=use_celery,
    )

    if idempotency_key:
        idempotency_store.complete_operation(idempotency_key, 202, result)

    return result


@router.get("", response_model=PaginatedResponse[PlanningRunResponse], summary="List Planning Runs")
async def list_planning_runs(
    current_user: Annotated[dict, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """Fetch paginated history of planning run executions."""
    repo = PlanningRepository(session)
    runs, total = await repo.list_runs(page=page, page_size=page_size)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return PaginatedResponse[PlanningRunResponse](
        items=[PlanningRunResponse.model_validate(r) for r in runs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/latest", response_model=Optional[PlanningRunDetailResponse], summary="Get Latest Planning Run")
async def get_latest_planning_run(
    current_user: Annotated[dict, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Retrieve the most recently executed planning run with KPI metrics."""
    service = PlanningService(session)
    return await service.get_latest_run()


@router.get("/{run_id}", response_model=PlanningRunDetailResponse, summary="Get Planning Run Details")
async def get_planning_run_detail(
    run_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """Retrieve full details, metrics, and KPI root cause breakdown of a planning run."""
    service = PlanningService(session)
    return await service.get_run_detail(run_id)


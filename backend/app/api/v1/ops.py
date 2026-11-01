"""SupplyChain IQ - Operations & Domain REST Endpoints."""

from typing import Annotated, Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_async_session, get_current_user
from backend.app.repositories.ops_repo import OpsRepository
from backend.app.schemas.common import PaginatedResponse

router = APIRouter(tags=["Operations & Control Tower"])


# --- 1. Dashboard Endpoints ---

@router.get("/dashboard/kpis", response_model=Dict[str, Any], summary="Get Executive Dashboard KPIs")
async def get_dashboard_kpis(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    repo = OpsRepository(session)
    return await repo.get_dashboard_kpis()


@router.get("/dashboard/charts", response_model=Dict[str, Any], summary="Get Executive Dashboard Charts Data")
async def get_dashboard_charts(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    current_user: Annotated[dict, Depends(get_current_user)],
):
    repo = OpsRepository(session)
    return await repo.get_dashboard_charts()


# --- 2. Demand Planning Endpoints ---

@router.get("/demand", response_model=PaginatedResponse[Dict[str, Any]], summary="List Forecast Demand Records")
async def list_demand(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    current_user: Annotated[dict, Depends(get_current_user)],
    week_bucket: Optional[str] = Query(default=None),
    sku_id: Optional[str] = Query(default=None),
    location_id: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
):
    repo = OpsRepository(session)
    items, total = await repo.list_demand(
        week_bucket=week_bucket,
        sku_id=sku_id,
        location_id=location_id,
        page=page,
        page_size=page_size,
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return PaginatedResponse[Dict[str, Any]](
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# --- 3. Inventory Management Endpoints ---

@router.get("/inventory", response_model=PaginatedResponse[Dict[str, Any]], summary="List Inventory Stock Snapshots")
async def list_inventory(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    current_user: Annotated[dict, Depends(get_current_user)],
    category: Optional[str] = Query(default=None),
    location_code: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
):
    repo = OpsRepository(session)
    items, total = await repo.list_inventory(
        category=category,
        location_code=location_code,
        page=page,
        page_size=page_size,
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return PaginatedResponse[Dict[str, Any]](
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# --- 4. Supplier Management Endpoints ---

@router.get("/suppliers/overview", response_model=PaginatedResponse[Dict[str, Any]], summary="List Suppliers Overview & Capacity")
async def list_suppliers(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    current_user: Annotated[dict, Depends(get_current_user)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
):
    repo = OpsRepository(session)
    items, total = await repo.list_suppliers_overview(page=page, page_size=page_size)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return PaginatedResponse[Dict[str, Any]](
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# --- 5. Purchase Orders Endpoints ---

@router.get("/purchase-orders", response_model=PaginatedResponse[Dict[str, Any]], summary="List Inbound Purchase Orders")
async def list_purchase_orders(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    current_user: Annotated[dict, Depends(get_current_user)],
    status: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
):
    repo = OpsRepository(session)
    items, total = await repo.list_purchase_orders(status=status, page=page, page_size=page_size)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return PaginatedResponse[Dict[str, Any]](
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# --- 6. Production Planning Endpoints ---

@router.get("/production-plans", response_model=PaginatedResponse[Dict[str, Any]], summary="List Production Orders")
async def list_production_plans(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    current_user: Annotated[dict, Depends(get_current_user)],
    status: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
):
    repo = OpsRepository(session)
    items, total = await repo.list_production_plans(status=status, page=page, page_size=page_size)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return PaginatedResponse[Dict[str, Any]](
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


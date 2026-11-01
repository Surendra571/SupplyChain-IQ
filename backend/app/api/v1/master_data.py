"""SupplyChain IQ - Master Data Lookups Router."""

from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_async_session, get_current_user
from backend.app.repositories.master_data_repo import MasterDataRepository
from backend.app.schemas.common import PaginatedResponse
from backend.app.schemas.master_data import LocationResponse, SKUResponse, SupplierResponse

router = APIRouter(prefix="/master-data", tags=["Master Data Lookups"])


@router.get("/skus", response_model=PaginatedResponse[SKUResponse], summary="List SKUs")
async def list_skus(
    current_user: Annotated[dict, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    sku_type: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
):
    repo = MasterDataRepository(session)
    skus, total = await repo.list_skus(sku_type=sku_type, page=page, page_size=page_size)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return PaginatedResponse[SKUResponse](
        items=[SKUResponse.model_validate(s) for s in skus],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/locations", response_model=PaginatedResponse[LocationResponse], summary="List Locations")
async def list_locations(
    current_user: Annotated[dict, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    location_type: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
):
    repo = MasterDataRepository(session)
    locs, total = await repo.list_locations(location_type=location_type, page=page, page_size=page_size)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return PaginatedResponse[LocationResponse](
        items=[LocationResponse.model_validate(l) for l in locs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/suppliers", response_model=PaginatedResponse[SupplierResponse], summary="List Suppliers")
async def list_suppliers(
    current_user: Annotated[dict, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
):
    repo = MasterDataRepository(session)
    supps, total = await repo.list_suppliers(page=page, page_size=page_size)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return PaginatedResponse[SupplierResponse](
        items=[SupplierResponse.model_validate(s) for s in supps],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


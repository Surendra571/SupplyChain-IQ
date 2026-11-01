"""SupplyChain IQ - Pydantic Schemas for Production, BOM & Substitution."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.enums import ProductionPlanStatus


class BOMBase(BaseModel):
    parent_sku_id: uuid.UUID
    bom_version: str = Field(default="v1.0", max_length=32)
    description: Optional[str] = None
    is_active: bool = True
    effective_from: datetime
    effective_to: Optional[datetime] = None


class BOMCreate(BOMBase):
    business_id: str = Field(..., max_length=64)


class BOMResponse(BOMBase):
    id: uuid.UUID
    business_id: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class BOMComponentBase(BaseModel):
    bom_id: uuid.UUID
    component_sku_id: uuid.UUID
    quantity_per_parent: Decimal = Field(..., gt=0, decimal_places=4)
    scrap_percentage: Decimal = Field(default=Decimal("0.0000"), ge=0, lt=1, decimal_places=4)
    lead_time_offset_days: int = Field(default=0, ge=0)


class BOMComponentCreate(BOMComponentBase):
    business_id: str = Field(..., max_length=64)


class BOMComponentResponse(BOMComponentBase):
    id: uuid.UUID
    business_id: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class SubstituteSKUBase(BaseModel):
    primary_sku_id: uuid.UUID
    substitute_sku_id: uuid.UUID
    conversion_factor: Decimal = Field(default=Decimal("1.0000"), gt=0, decimal_places=4)
    preference_rank: int = Field(default=1, ge=1)
    is_bidirectional: bool = False
    effective_from: datetime
    effective_to: Optional[datetime] = None


class SubstituteSKUCreate(SubstituteSKUBase):
    business_id: str = Field(..., max_length=64)


class SubstituteSKUResponse(SubstituteSKUBase):
    id: uuid.UUID
    business_id: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ProductionPlanBase(BaseModel):
    sku_id: uuid.UUID
    location_id: uuid.UUID
    week_bucket: str = Field(..., max_length=16)
    planned_quantity: int = Field(..., ge=0)
    status: ProductionPlanStatus = ProductionPlanStatus.PLANNED
    work_center_id: Optional[str] = None


class ProductionPlanCreate(ProductionPlanBase):
    business_id: str = Field(..., max_length=64)


class ProductionPlanResponse(ProductionPlanBase):
    id: uuid.UUID
    business_id: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


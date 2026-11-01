"""SupplyChain IQ - Pydantic Schemas for Master Data."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.enums import LocationType, SKUType, SupplierTier, TransportMode


class SKUBase(BaseModel):
    sku_code: str = Field(..., max_length=64, description="Unique SKU code")
    name: str = Field(..., max_length=255, description="SKU Name")
    category: str = Field(..., max_length=100, description="Product category")
    sku_type: SKUType
    unit_of_measure: str = Field(default="EA", max_length=20)
    unit_cost: Decimal = Field(..., ge=0, decimal_places=4)
    unit_price: Decimal = Field(..., ge=0, decimal_places=4)
    weight_kg: Decimal = Field(default=Decimal("0.000"), ge=0, decimal_places=3)
    is_active: bool = True


class SKUCreate(SKUBase):
    business_id: str = Field(..., max_length=64)


class SKUResponse(SKUBase):
    id: uuid.UUID
    business_id: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class LocationBase(BaseModel):
    location_code: str = Field(..., max_length=64)
    name: str = Field(..., max_length=255)
    location_type: LocationType
    capacity_units: int = Field(default=0, ge=0)
    country: str = Field(..., max_length=3)
    is_active: bool = True


class LocationCreate(LocationBase):
    business_id: str = Field(..., max_length=64)


class LocationResponse(LocationBase):
    id: uuid.UUID
    business_id: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class SupplierBase(BaseModel):
    supplier_code: str = Field(..., max_length=64)
    name: str = Field(..., max_length=255)
    tier: SupplierTier = SupplierTier.TIER_1
    country: str = Field(..., max_length=3)
    payment_terms: str = Field(default="NET30", max_length=64)
    on_time_delivery_rate: Decimal = Field(default=Decimal("0.9500"), ge=0, le=1, decimal_places=4)
    is_active: bool = True


class SupplierCreate(SupplierBase):
    business_id: str = Field(..., max_length=64)


class SupplierResponse(SupplierBase):
    id: uuid.UUID
    business_id: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class SupplierSKUBase(BaseModel):
    supplier_id: uuid.UUID
    sku_id: uuid.UUID
    unit_price: Decimal = Field(..., ge=0, decimal_places=4)
    moq: int = Field(default=1, ge=1)
    pack_size: int = Field(default=1, ge=1)
    lead_time_days: int = Field(default=7, ge=1)
    is_preferred: bool = False
    effective_from: datetime
    effective_to: Optional[datetime] = None


class SupplierSKUCreate(SupplierSKUBase):
    business_id: str = Field(..., max_length=64)


class SupplierSKUResponse(SupplierSKUBase):
    id: uuid.UUID
    business_id: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class LeadTimeBase(BaseModel):
    origin_location_id: uuid.UUID
    destination_location_id: uuid.UUID
    transport_mode: TransportMode = TransportMode.ROAD
    transit_days: int = Field(default=1, ge=0)
    variability_days: int = Field(default=0, ge=0)
    cost_per_unit: Decimal = Field(default=Decimal("0.0000"), ge=0, decimal_places=4)
    effective_from: datetime
    effective_to: Optional[datetime] = None


class LeadTimeCreate(LeadTimeBase):
    business_id: str = Field(..., max_length=64)


class LeadTimeResponse(LeadTimeBase):
    id: uuid.UUID
    business_id: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


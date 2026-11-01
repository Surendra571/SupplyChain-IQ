"""SupplyChain IQ - Pydantic Schemas for Procurement, POs & Shipments."""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.enums import PurchaseOrderStatus, ShipmentStatus


class SupplierCapacityBase(BaseModel):
    supplier_id: uuid.UUID
    sku_id: uuid.UUID
    week_bucket: str = Field(..., max_length=16)
    max_capacity_units: int = Field(..., ge=0)
    committed_units: int = Field(default=0, ge=0)
    surge_capacity_units: int = Field(default=0, ge=0)


class SupplierCapacityCreate(SupplierCapacityBase):
    business_id: str = Field(..., max_length=64)


class SupplierCapacityResponse(SupplierCapacityBase):
    id: uuid.UUID
    business_id: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PurchaseOrderLineBase(BaseModel):
    po_id: uuid.UUID
    line_number: int = Field(..., ge=1)
    sku_id: uuid.UUID
    destination_location_id: uuid.UUID
    ordered_qty: int = Field(..., gt=0)
    received_qty: int = Field(default=0, ge=0)
    unit_cost: Decimal = Field(..., ge=0, decimal_places=4)
    promised_delivery_date: datetime


class PurchaseOrderLineCreate(PurchaseOrderLineBase):
    business_id: str = Field(..., max_length=64)


class PurchaseOrderLineResponse(PurchaseOrderLineBase):
    id: uuid.UUID
    business_id: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PurchaseOrderBase(BaseModel):
    po_number: str = Field(..., max_length=64)
    supplier_id: uuid.UUID
    status: PurchaseOrderStatus = PurchaseOrderStatus.DRAFT
    order_date: datetime
    total_amount: Decimal = Field(default=Decimal("0.00"), ge=0, decimal_places=2)


class PurchaseOrderCreate(PurchaseOrderBase):
    business_id: str = Field(..., max_length=64)


class PurchaseOrderResponse(PurchaseOrderBase):
    id: uuid.UUID
    business_id: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ShipmentBase(BaseModel):
    po_id: uuid.UUID
    carrier_code: str = Field(..., max_length=64)
    tracking_number: str = Field(..., max_length=128)
    status: ShipmentStatus = ShipmentStatus.DISPATCHED
    origin_location_id: Optional[uuid.UUID] = None
    destination_location_id: uuid.UUID
    etd: datetime
    eta: datetime
    actual_delivery_date: Optional[datetime] = None


class ShipmentCreate(ShipmentBase):
    business_id: str = Field(..., max_length=64)


class ShipmentResponse(ShipmentBase):
    id: uuid.UUID
    business_id: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


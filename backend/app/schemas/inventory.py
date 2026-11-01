"""SupplyChain IQ - Pydantic Schemas for Inventory & Transactions."""

from datetime import datetime
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.enums import InventoryTransactionType


class InventoryBase(BaseModel):
    sku_id: uuid.UUID
    location_id: uuid.UUID
    on_hand_qty: int = Field(default=0, ge=0)
    allocated_qty: int = Field(default=0, ge=0)
    safety_stock_qty: int = Field(default=0, ge=0)
    reorder_point: int = Field(default=0, ge=0)
    last_counted_at: datetime


class InventoryCreate(InventoryBase):
    business_id: str = Field(..., max_length=64)


class InventoryResponse(InventoryBase):
    id: uuid.UUID
    business_id: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class InventoryTransactionBase(BaseModel):
    sku_id: uuid.UUID
    location_id: uuid.UUID
    transaction_type: InventoryTransactionType
    quantity: int
    balance_after: int = Field(..., ge=0)
    reference_id: Optional[str] = None
    notes: Optional[str] = None


class InventoryTransactionCreate(InventoryTransactionBase):
    business_id: str = Field(..., max_length=64)


class InventoryTransactionResponse(InventoryTransactionBase):
    id: uuid.UUID
    business_id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


"""SupplyChain IQ - Pydantic Schemas for Audit Events."""

from datetime import datetime
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field


class AuditEventBase(BaseModel):
    entity_name: str = Field(..., max_length=64)
    entity_id: str = Field(..., max_length=128)
    action: str = Field(..., max_length=32)
    performed_by: str = Field(..., max_length=64)
    before_state_json: Optional[str] = None
    after_state_json: Optional[str] = None
    created_at: datetime


class AuditEventCreate(AuditEventBase):
    business_id: str = Field(..., max_length=64)


class AuditEventResponse(AuditEventBase):
    id: uuid.UUID
    business_id: str
    model_config = ConfigDict(from_attributes=True)


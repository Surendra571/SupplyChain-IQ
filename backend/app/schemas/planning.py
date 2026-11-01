"""SupplyChain IQ - Pydantic Schemas for Planning Runs, Shortages & Mitigations."""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.enums import (
    MitigationActionType,
    MitigationDecisionType,
    MitigationOptionStatus,
    PlanningRunStatus,
    ShortageSeverity,
    ShortageStatus,
)


class PlanningRunBase(BaseModel):
    run_number: int = Field(..., ge=1)
    status: PlanningRunStatus = PlanningRunStatus.QUEUED
    horizon_weeks: int = Field(default=26, ge=1, le=104)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    config_json: Optional[str] = None
    summary_json: Optional[str] = None
    is_superseded: bool = False


class PlanningRunCreate(PlanningRunBase):
    business_id: str = Field(..., max_length=64)


class PlanningRunResponse(PlanningRunBase):
    id: uuid.UUID
    business_id: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ShortageBase(BaseModel):
    planning_run_id: uuid.UUID
    sku_id: uuid.UUID
    location_id: uuid.UUID
    week_bucket: str = Field(..., max_length=16)
    projected_deficit_qty: int = Field(..., gt=0)
    demand_shortage_qty: int = Field(default=0, ge=0)
    safety_stock_gap_qty: int = Field(default=0, ge=0)
    severity: ShortageSeverity
    priority_tier: Optional[str] = Field(default=None, max_length=32)
    priority_score: Decimal = Field(default=Decimal("0.00"), ge=0, le=100, decimal_places=2)
    financial_impact: Decimal = Field(default=Decimal("0.00"), ge=0, decimal_places=2)
    root_cause: Optional[str] = Field(default=None, max_length=64)
    root_cause_explanation: Optional[str] = None
    details_json: Optional[str] = None
    status: ShortageStatus = ShortageStatus.DETECTED


class ShortageCreate(ShortageBase):
    business_id: str = Field(..., max_length=64)


class ShortageResponse(ShortageBase):
    id: uuid.UUID
    business_id: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class MitigationOptionBase(BaseModel):
    shortage_id: uuid.UUID
    action_type: MitigationActionType
    status: MitigationOptionStatus = MitigationOptionStatus.PROPOSED
    recommended_qty: int = Field(..., gt=0)
    source_reference_id: Optional[str] = None
    incremental_cost: Decimal = Field(default=Decimal("0.00"), ge=0, decimal_places=2)
    service_gain_score: Decimal = Field(default=Decimal("100.00"), ge=0, le=100, decimal_places=2)
    roi_ratio: Decimal = Field(default=Decimal("0.0000"), decimal_places=4)
    rank: int = Field(default=1, ge=1)
    details_json: Optional[str] = None


class MitigationOptionCreate(MitigationOptionBase):
    business_id: str = Field(..., max_length=64)


class MitigationOptionResponse(MitigationOptionBase):
    id: uuid.UUID
    business_id: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class MitigationDecisionBase(BaseModel):
    mitigation_option_id: uuid.UUID
    planner_id: str = Field(..., max_length=64)
    decision: MitigationDecisionType
    override_qty: Optional[int] = Field(default=None, gt=0)
    reason: str
    decided_at: datetime


class MitigationDecisionCreate(MitigationDecisionBase):
    business_id: str = Field(..., max_length=64)


class MitigationDecisionResponse(MitigationDecisionBase):
    id: uuid.UUID
    business_id: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


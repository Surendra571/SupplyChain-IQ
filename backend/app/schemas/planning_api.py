"""SupplyChain IQ - Enriched Planning & Shortage API Schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
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


class PlanningRunTriggerRequest(BaseModel):
    """Payload to trigger or queue a new planning run."""
    horizon_weeks: int = Field(default=12, ge=1, le=52, description="Simulation horizon in weeks")
    data_dir: Optional[str] = Field(default=None, description="Optional custom dataset directory")
    persist_db: bool = Field(default=True, description="Whether to persist results directly into database")


class PlanningRunDetailResponse(BaseModel):
    """Full detail of a planning run execution."""
    id: uuid.UUID
    business_id: str
    run_number: int
    status: PlanningRunStatus
    horizon_weeks: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_time_seconds: Optional[float] = None
    total_projections: int = 0
    total_shortages: int = 0
    critical_shortages: int = 0
    warning_shortages: int = 0
    total_demand_shortage_qty: int = 0
    total_safety_stock_gap_qty: int = 0
    total_financial_impact: float = 0.0
    root_cause_breakdown: Dict[str, int] = {}
    priority_breakdown: Dict[str, int] = {}
    is_superseded: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ShortageFilterParams(BaseModel):
    """Query filter parameters for shortages workbench."""
    planning_run_id: Optional[str] = None
    severity: Optional[ShortageSeverity] = None
    priority_tier: Optional[str] = None
    status: Optional[ShortageStatus] = None
    sku_code: Optional[str] = None
    location_code: Optional[str] = None
    week_bucket: Optional[str] = None
    root_cause: Optional[str] = None
    min_priority_score: Optional[float] = None
    max_priority_score: Optional[float] = None


class ShortageEnrichedResponse(BaseModel):
    """Shortage record enriched with master data codes and names."""
    id: uuid.UUID
    business_id: str
    planning_run_id: uuid.UUID
    sku_id: uuid.UUID
    sku_code: str
    sku_name: str
    unit_of_measure: str
    location_id: uuid.UUID
    location_code: str
    location_name: str
    location_type: str
    week_bucket: str
    projected_deficit_qty: int
    demand_shortage_qty: int
    safety_stock_gap_qty: int
    severity: ShortageSeverity
    priority_tier: Optional[str] = None
    priority_score: Decimal
    financial_impact: Decimal
    root_cause: Optional[str] = None
    root_cause_explanation: Optional[str] = None
    status: ShortageStatus
    has_mitigation: bool = False
    recommended_action: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TimePhasedPABPoint(BaseModel):
    """Single weekly bucket projection in the time-phased balance curve."""
    week_bucket: str
    week_index: int
    opening_balance: int
    forecast_demand: int
    scheduled_receipts: int
    planned_production: int
    transfers_in: int
    transfers_out: int
    allocated_qty: int
    safety_stock: int
    projected_available_balance: int
    demand_shortage: int
    safety_stock_gap: int
    stockout_risk: bool


class ShortagePABDetailResponse(BaseModel):
    """Time-series inventory curve for a specific SKU-Location pair."""
    sku_code: str
    sku_name: str
    location_code: str
    location_name: str
    shortage_week: str
    points: List[TimePhasedPABPoint]


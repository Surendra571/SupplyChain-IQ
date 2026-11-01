"""SupplyChain IQ - Planning Engine Data Models, Enums & Schemas."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.enums import ShortageSeverity, ShortageStatus


class ShortageRootCause(str, Enum):
    """Recognized root cause categories for projected inventory shortages."""
    DEMAND_SPIKE = "Demand spike"
    INSUFFICIENT_OPENING_INVENTORY = "Insufficient opening inventory"
    SUPPLIER_DELAY = "Supplier delay"
    SUPPLIER_CAPACITY_SHORTAGE = "Supplier capacity shortage"
    PRODUCTION_CONSTRAINT = "Production constraint"
    TRANSPORTATION_DELAY = "Transportation delay"
    MISSING_LEAD_TIME = "Missing lead time"
    INVALID_SUBSTITUTE = "Invalid substitute"


class PriorityTier(str, Enum):
    """Categorical triage priority tiers for planners."""
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class PlanningConfig(BaseModel):
    """Configurable scoring weights, thresholds, and simulation parameters."""
    horizon_weeks: int = Field(default=12, ge=1, le=104)
    # Priority scoring weights (sum to 1.0)
    w_days: float = Field(default=0.25, ge=0.0, le=1.0)
    w_qty: float = Field(default=0.20, ge=0.0, le=1.0)
    w_financial: float = Field(default=0.25, ge=0.0, le=1.0)
    w_criticality: float = Field(default=0.15, ge=0.0, le=1.0)
    w_recovery: float = Field(default=0.15, ge=0.0, le=1.0)

    # Priority tier score boundaries
    threshold_critical: float = Field(default=75.0, ge=0.0, le=100.0)
    threshold_high: float = Field(default=50.0, ge=0.0, le=100.0)
    threshold_medium: float = Field(default=25.0, ge=0.0, le=100.0)

    # Normalization scaling caps
    financial_ceiling: float = Field(default=50000.0, gt=0.0)
    demand_spike_multiplier: float = Field(default=1.5, gt=1.0)


class WeeklyProjection(BaseModel):
    """Time-phased projected available balance and components for a single SKU-Location-Week."""
    sku_id: str
    sku_code: str
    location_id: str
    location_code: str
    week_bucket: str
    week_index: int
    unit_of_measure: str

    opening_pab: int = Field(description="Projected available balance at the start of period t (PAB[t-1])")
    purchase_receipts: int = Field(default=0, description="Scheduled and verified PO receipts arriving in period t")
    production_receipts: int = Field(default=0, description="Feasible scheduled manufacturing receipts in period t")
    transfers_in: int = Field(default=0, description="Inbound inter-facility transfer receipts in period t")
    forecast_demand: int = Field(default=0, description="Forecast gross customer demand in period t")
    allocations: int = Field(default=0, description="Inventory reservations or allocated stock in period t")
    transfers_out: int = Field(default=0, description="Outbound inter-facility transfers in period t")

    available_before_demand: int = Field(
        description="Available supply before satisfying forecast demand: PAB[t-1] + Receipts - Allocations - TransfersOut"
    )
    closing_pab: int = Field(
        description="Closing projected available balance at end of period t (AvailableBeforeDemand - ForecastDemand)"
    )
    safety_stock: int = Field(default=0, description="Target safety stock buffer threshold")

    demand_shortage: int = Field(
        default=0,
        description="Unfulfilled forecast demand: MAX(0, ForecastDemand - AvailableBeforeDemand)"
    )
    safety_stock_gap: int = Field(
        default=0,
        description="Deficit below safety stock target: MAX(0, SafetyStock - ClosingPAB)"
    )

    model_config = ConfigDict(from_attributes=True)


class ShortageOutput(BaseModel):
    """Detailed shortage record identified by the planning engine."""
    business_id: str
    planning_run_id: str
    sku_id: str
    sku_code: str
    sku_name: str
    location_id: str
    location_code: str
    location_name: str
    week_bucket: str
    week_index: int
    days_until_stockout: int

    projected_deficit_qty: int = Field(description="Total units required to restore inventory to safety stock")
    demand_shortage_qty: int = Field(description="Unmet customer demand: MAX(0, ForecastDemand - AvailableBeforeDemand)")
    safety_stock_gap_qty: int = Field(description="Safety stock buffer deficit: MAX(0, SafetyStock - ClosingPAB)")

    severity: ShortageSeverity = Field(description="CRITICAL if ClosingPAB < 0 else WARNING")
    priority_tier: PriorityTier = Field(description="Critical, High, Medium, or Low")
    priority_score: float = Field(ge=0.0, le=100.0, description="Composite urgency score (0-100)")
    financial_impact: float = Field(ge=0.0, description="Financial value at risk (ShortageQty * Unit Cost)")

    root_cause: ShortageRootCause = Field(description="Primary diagnosed root cause category")
    root_cause_explanation: str = Field(description="Human-readable contextual explanation")

    score_breakdown: Dict[str, float] = Field(default_factory=dict)
    details: Dict[str, Any] = Field(default_factory=dict)
    status: ShortageStatus = ShortageStatus.DETECTED

    model_config = ConfigDict(from_attributes=True)


class PlanningRunSummary(BaseModel):
    """Immutable execution summary for a completed supply-demand planning run."""
    run_id: str
    run_number: int
    horizon_weeks: int
    total_skus: int
    total_locations: int
    total_projections: int
    total_shortages: int
    critical_shortages: int
    warning_shortages: int
    total_demand_shortage_qty: int
    total_safety_stock_gap_qty: int
    total_financial_impact: float
    root_cause_breakdown: Dict[str, int]
    priority_breakdown: Dict[str, int]
    started_at: str
    completed_at: str
    execution_time_seconds: float
    config: Dict[str, Any]


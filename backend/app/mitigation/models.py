"""SupplyChain IQ - Mitigation Data Models, Options & Comparison Schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.enums import MitigationActionType, MitigationOptionStatus


class MitigationConfig(BaseModel):
    """Configuration weights and cost parameters for mitigation planning."""
    air_freight_premium_per_unit: float = Field(default=2.50, description="Additional per-unit cost for expedited air freight")
    expedited_lead_time_factor: float = Field(default=0.40, description="Lead time compression ratio for expedited shipment (e.g. 40% of standard)")
    min_expedited_days: int = Field(default=2, description="Minimum days for expedited freight")
    production_setup_cost: float = Field(default=500.0, description="Fixed setup cost for unscheduled production run")
    production_overtime_cost_per_unit: float = Field(default=5.0, description="Additional per-unit labor/overtime cost for production increase")
    default_transfer_cost_per_unit: float = Field(default=1.20, description="Fallback freight cost per unit for inter-facility transfers")
    cost_penalty_weight: float = Field(default=0.001, description="Weight of incremental cost penalty in optimization objective")


class MitigationCandidate(BaseModel):
    """Single candidate mitigation action evaluated for a shortage."""
    candidate_id: str = Field(default_factory=lambda: f"CAND-{uuid.uuid4().hex[:8]}")
    shortage_id: str
    action_type: MitigationActionType
    status: MitigationOptionStatus = MitigationOptionStatus.PROPOSED

    sku_id: str
    sku_code: str
    location_id: str
    location_code: str
    target_week: str

    recoverable_quantity: int = Field(ge=0, description="Quantity feasible to recover through this option")
    quantity_still_at_risk: int = Field(ge=0, description="Remaining shortage deficit after applying option")

    additional_procurement_cost: float = Field(default=0.0, ge=0.0)
    transportation_cost: float = Field(default=0.0, ge=0.0)
    production_cost: float = Field(default=0.0, ge=0.0)
    total_cost: float = Field(default=0.0, ge=0.0)

    expected_arrival_date: str
    expected_arrival_week: str
    recovery_time_days: int = Field(ge=0)

    service_level_impact: float = Field(ge=0.0, le=100.0, description="Service percentage or protected fill rate gain (0-100)")
    roi_ratio: float = Field(default=0.0, description="Financial protection ratio (Revenue at Risk saved / Total Cost)")
    rank: int = Field(default=1, ge=1)

    is_feasible: bool = Field(description="Strict feasibility status honoring all physical & contract constraints")
    infeasibility_reasons: List[str] = Field(default_factory=list)

    source_reference_id: Optional[str] = Field(default=None, description="PO ID, Supplier ID, Source Location, or Plant ID")
    explanation: str = Field(description="Contextual business explanation of proposed action and tradeoffs")
    details: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class MitigationComparison(BaseModel):
    """Comparison view of candidate options for a specific shortage event."""
    shortage_id: str
    sku_code: str
    location_code: str
    week_bucket: str
    projected_deficit_qty: int

    cheapest_option: Optional[MitigationCandidate] = None
    fastest_option: Optional[MitigationCandidate] = None
    best_service_option: Optional[MitigationCandidate] = None
    recommended_option: Optional[MitigationCandidate] = None

    all_options: List[MitigationCandidate] = Field(default_factory=list)
    comparison_summary: str = Field(default="")

    model_config = ConfigDict(from_attributes=True)


class MitigationPlanSummary(BaseModel):
    """Execution summary of the mitigation engine and optimization solver."""
    planning_run_id: str
    total_shortages: int
    mitigated_shortages: int
    unmitigated_shortages: int
    total_deficit_qty: int
    total_recovered_qty: int
    total_mitigation_cost: float
    total_revenue_protected: float
    average_service_gain: float
    solver_status: str
    execution_time_seconds: float
    recommended_options_count: int


"""SupplyChain IQ - Decision & Mitigation API Schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.enums import (
    MitigationActionType,
    MitigationDecisionType,
    MitigationOptionStatus,
)


class MitigationOptionItem(BaseModel):
    """Enriched mitigation candidate option."""
    id: uuid.UUID
    business_id: str
    shortage_id: uuid.UUID
    action_type: MitigationActionType
    status: MitigationOptionStatus
    recommended_qty: int
    source_reference_id: Optional[str] = None
    incremental_cost: Decimal
    service_gain_score: Decimal
    roi_ratio: Decimal
    rank: int
    details: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MitigationComparisonView(BaseModel):
    """Four-way trade-off analysis for a shortage."""
    shortage_id: str
    sku_code: str
    location_code: str
    week_bucket: str
    projected_deficit_qty: int
    cheapest_option: Optional[Dict[str, Any]] = None
    fastest_option: Optional[Dict[str, Any]] = None
    best_service_option: Optional[Dict[str, Any]] = None
    recommended_option: Optional[Dict[str, Any]] = None
    all_candidates: List[MitigationOptionItem] = []
    comparison_summary: str


class DecisionSubmitRequest(BaseModel):
    """Planner decision submission payload."""
    mitigation_option_id: str = Field(..., description="Target MitigationOption UUID or Business ID")
    decision: MitigationDecisionType = Field(..., description="Decision type: APPROVED, REJECTED, or OVERRIDDEN")
    override_qty: Optional[int] = Field(default=None, ge=1, description="Quantity when decision is OVERRIDDEN")
    reason: str = Field(..., min_length=5, description="Business justification required for audit compliance")


class DecisionSubmitResponse(BaseModel):
    """Immutable decision confirmation record."""
    id: uuid.UUID
    business_id: str
    mitigation_option_id: uuid.UUID
    planner_id: str
    decision: MitigationDecisionType
    override_qty: Optional[int] = None
    reason: str
    decided_at: datetime
    status: str
    message: str

    model_config = ConfigDict(from_attributes=True)


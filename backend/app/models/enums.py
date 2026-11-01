"""SupplyChain IQ - Core Business Enums & Lifecycle State Machines."""

from enum import Enum
from typing import Dict, Set


class SKUType(str, Enum):
    FINISHED_GOOD = "FINISHED_GOOD"
    SUBASSEMBLY = "SUBASSEMBLY"
    RAW_MATERIAL = "RAW_MATERIAL"


class LocationType(str, Enum):
    PLANT = "PLANT"
    DC = "DC"
    WAREHOUSE = "WAREHOUSE"
    HUB = "HUB"
    RETAIL = "RETAIL"


class SupplierTier(str, Enum):
    TIER_1 = "TIER_1"
    TIER_2 = "TIER_2"
    TIER_3 = "TIER_3"
    STRATEGIC = "STRATEGIC"


class TransportMode(str, Enum):
    ROAD = "ROAD"
    RAIL = "RAIL"
    AIR = "AIR"
    OCEAN = "OCEAN"


class InventoryTransactionType(str, Enum):
    RECEIPT = "RECEIPT"
    ISSUE = "ISSUE"
    ADJUSTMENT = "ADJUSTMENT"
    TRANSFER_IN = "TRANSFER_IN"
    TRANSFER_OUT = "TRANSFER_OUT"
    SCRAP = "SCRAP"


class PurchaseOrderStatus(str, Enum):
    DRAFT = "DRAFT"
    PLACED = "PLACED"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class ShipmentStatus(str, Enum):
    DISPATCHED = "DISPATCHED"
    IN_TRANSIT = "IN_TRANSIT"
    CUSTOMS = "CUSTOMS"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class ProductionPlanStatus(str, Enum):
    DRAFT = "DRAFT"
    PLANNED = "PLANNED"
    FIRM = "FIRM"
    RELEASED = "RELEASED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ShortageSeverity(str, Enum):
    WARNING = "WARNING"    # 0 <= PAB < Safety Stock
    CRITICAL = "CRITICAL"  # PAB < 0


class ShortageStatus(str, Enum):
    DETECTED = "DETECTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    MITIGATED = "MITIGATED"
    RESOLVED = "RESOLVED"
    IGNORED = "IGNORED"


class MitigationActionType(str, Enum):
    EXISTING_SUPPLIER_PROCUREMENT = "EXISTING_SUPPLIER_PROCUREMENT"
    ALTERNATIVE_APPROVED_SUPPLIER = "ALTERNATIVE_APPROVED_SUPPLIER"
    EXPEDITED_SHIPMENT = "EXPEDITED_SHIPMENT"
    INVENTORY_TRANSFER = "INVENTORY_TRANSFER"
    PRODUCTION_INCREASE = "PRODUCTION_INCREASE"
    APPROVED_SUBSTITUTE_SKU = "APPROVED_SUBSTITUTE_SKU"
    PARTIAL_FULFILLMENT = "PARTIAL_FULFILLMENT"
    # Aliases for backward compatibility
    EXPEDITE_PO = "EXPEDITE_PO"
    ALTERNATE_SUPPLIER = "ALTERNATE_SUPPLIER"
    SKU_SUBSTITUTION = "SKU_SUBSTITUTION"
    INTER_FACILITY_TRANSFER = "INTER_FACILITY_TRANSFER"
    PRODUCTION_RESCHEDULE = "PRODUCTION_RESCHEDULE"


class MitigationOptionStatus(str, Enum):
    PROPOSED = "PROPOSED"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class MitigationDecisionType(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    OVERRIDDEN = "OVERRIDDEN"


class PlanningRunStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# ---------------------------------------------------------------------------
# Lifecycle State Transition Validation Rules
# ---------------------------------------------------------------------------

ALLOWED_PO_TRANSITIONS: Dict[PurchaseOrderStatus, Set[PurchaseOrderStatus]] = {
    PurchaseOrderStatus.DRAFT: {PurchaseOrderStatus.PLACED, PurchaseOrderStatus.CANCELLED},
    PurchaseOrderStatus.PLACED: {PurchaseOrderStatus.IN_TRANSIT, PurchaseOrderStatus.DELIVERED, PurchaseOrderStatus.CANCELLED},
    PurchaseOrderStatus.IN_TRANSIT: {PurchaseOrderStatus.DELIVERED, PurchaseOrderStatus.CANCELLED},
    PurchaseOrderStatus.DELIVERED: set(),
    PurchaseOrderStatus.CANCELLED: set(),
}

ALLOWED_SHIPMENT_TRANSITIONS: Dict[ShipmentStatus, Set[ShipmentStatus]] = {
    ShipmentStatus.DISPATCHED: {ShipmentStatus.IN_TRANSIT, ShipmentStatus.CANCELLED},
    ShipmentStatus.IN_TRANSIT: {ShipmentStatus.CUSTOMS, ShipmentStatus.DELIVERED, ShipmentStatus.CANCELLED},
    ShipmentStatus.CUSTOMS: {ShipmentStatus.IN_TRANSIT, ShipmentStatus.DELIVERED, ShipmentStatus.CANCELLED},
    ShipmentStatus.DELIVERED: set(),
    ShipmentStatus.CANCELLED: set(),
}

ALLOWED_PRODUCTION_TRANSITIONS: Dict[ProductionPlanStatus, Set[ProductionPlanStatus]] = {
    ProductionPlanStatus.DRAFT: {ProductionPlanStatus.PLANNED, ProductionPlanStatus.CANCELLED},
    ProductionPlanStatus.PLANNED: {ProductionPlanStatus.FIRM, ProductionPlanStatus.CANCELLED},
    ProductionPlanStatus.FIRM: {ProductionPlanStatus.RELEASED, ProductionPlanStatus.CANCELLED},
    ProductionPlanStatus.RELEASED: {ProductionPlanStatus.IN_PROGRESS, ProductionPlanStatus.CANCELLED},
    ProductionPlanStatus.IN_PROGRESS: {ProductionPlanStatus.COMPLETED, ProductionPlanStatus.CANCELLED},
    ProductionPlanStatus.COMPLETED: set(),
    ProductionPlanStatus.CANCELLED: set(),
}

ALLOWED_SHORTAGE_TRANSITIONS: Dict[ShortageStatus, Set[ShortageStatus]] = {
    ShortageStatus.DETECTED: {ShortageStatus.ACKNOWLEDGED, ShortageStatus.MITIGATED, ShortageStatus.IGNORED},
    ShortageStatus.ACKNOWLEDGED: {ShortageStatus.MITIGATED, ShortageStatus.RESOLVED, ShortageStatus.IGNORED},
    ShortageStatus.MITIGATED: {ShortageStatus.RESOLVED, ShortageStatus.DETECTED},
    ShortageStatus.RESOLVED: set(),
    ShortageStatus.IGNORED: {ShortageStatus.DETECTED},
}

ALLOWED_MITIGATION_TRANSITIONS: Dict[MitigationOptionStatus, Set[MitigationOptionStatus]] = {
    MitigationOptionStatus.PROPOSED: {MitigationOptionStatus.UNDER_REVIEW, MitigationOptionStatus.APPROVED, MitigationOptionStatus.REJECTED, MitigationOptionStatus.EXPIRED},
    MitigationOptionStatus.UNDER_REVIEW: {MitigationOptionStatus.APPROVED, MitigationOptionStatus.REJECTED, MitigationOptionStatus.EXPIRED},
    MitigationOptionStatus.APPROVED: set(),
    MitigationOptionStatus.REJECTED: set(),
    MitigationOptionStatus.EXPIRED: set(),
}

ALLOWED_PLANNING_RUN_TRANSITIONS: Dict[PlanningRunStatus, Set[PlanningRunStatus]] = {
    PlanningRunStatus.QUEUED: {PlanningRunStatus.RUNNING, PlanningRunStatus.FAILED},
    PlanningRunStatus.RUNNING: {PlanningRunStatus.COMPLETED, PlanningRunStatus.FAILED},
    PlanningRunStatus.COMPLETED: set(),
    PlanningRunStatus.FAILED: set(),
}


def validate_transition(current_state, next_state, allowed_map) -> bool:
    """Validate if transitioning from current_state to next_state is valid."""
    if current_state == next_state:
        return True
    allowed = allowed_map.get(current_state, set())
    return next_state in allowed


"""Tests for Lifecycle State Machines and Invalid Transition Prevention."""

import pytest

from backend.app.models.enums import (
    ALLOWED_MITIGATION_TRANSITIONS,
    ALLOWED_PLANNING_RUN_TRANSITIONS,
    ALLOWED_PO_TRANSITIONS,
    ALLOWED_PRODUCTION_TRANSITIONS,
    ALLOWED_SHIPMENT_TRANSITIONS,
    ALLOWED_SHORTAGE_TRANSITIONS,
    MitigationOptionStatus,
    PlanningRunStatus,
    ProductionPlanStatus,
    PurchaseOrderStatus,
    ShipmentStatus,
    ShortageStatus,
    validate_transition,
)


def test_purchase_order_lifecycle():
    """Verify PurchaseOrder allowed and forbidden transitions."""
    # Valid forward transitions
    assert validate_transition(PurchaseOrderStatus.DRAFT, PurchaseOrderStatus.PLACED, ALLOWED_PO_TRANSITIONS) is True
    assert validate_transition(PurchaseOrderStatus.PLACED, PurchaseOrderStatus.IN_TRANSIT, ALLOWED_PO_TRANSITIONS) is True
    assert validate_transition(PurchaseOrderStatus.IN_TRANSIT, PurchaseOrderStatus.DELIVERED, ALLOWED_PO_TRANSITIONS) is True

    # Valid cancellations
    assert validate_transition(PurchaseOrderStatus.DRAFT, PurchaseOrderStatus.CANCELLED, ALLOWED_PO_TRANSITIONS) is True
    assert validate_transition(PurchaseOrderStatus.PLACED, PurchaseOrderStatus.CANCELLED, ALLOWED_PO_TRANSITIONS) is True

    # Same state is always valid
    assert validate_transition(PurchaseOrderStatus.PLACED, PurchaseOrderStatus.PLACED, ALLOWED_PO_TRANSITIONS) is True

    # Invalid jump: DRAFT straight to DELIVERED
    assert validate_transition(PurchaseOrderStatus.DRAFT, PurchaseOrderStatus.DELIVERED, ALLOWED_PO_TRANSITIONS) is False

    # Invalid reverse: DELIVERED back to DRAFT or PLACED
    assert validate_transition(PurchaseOrderStatus.DELIVERED, PurchaseOrderStatus.DRAFT, ALLOWED_PO_TRANSITIONS) is False
    assert validate_transition(PurchaseOrderStatus.DELIVERED, PurchaseOrderStatus.PLACED, ALLOWED_PO_TRANSITIONS) is False


def test_shipment_lifecycle():
    """Verify Shipment allowed and forbidden transitions."""
    assert validate_transition(ShipmentStatus.DISPATCHED, ShipmentStatus.IN_TRANSIT, ALLOWED_SHIPMENT_TRANSITIONS) is True
    assert validate_transition(ShipmentStatus.IN_TRANSIT, ShipmentStatus.CUSTOMS, ALLOWED_SHIPMENT_TRANSITIONS) is True
    assert validate_transition(ShipmentStatus.CUSTOMS, ShipmentStatus.DELIVERED, ALLOWED_SHIPMENT_TRANSITIONS) is True

    # Invalid transition: DISPATCHED straight to DELIVERED without transit
    assert validate_transition(ShipmentStatus.DISPATCHED, ShipmentStatus.DELIVERED, ALLOWED_SHIPMENT_TRANSITIONS) is False
    # Terminal state: DELIVERED cannot transition anywhere
    assert validate_transition(ShipmentStatus.DELIVERED, ShipmentStatus.IN_TRANSIT, ALLOWED_SHIPMENT_TRANSITIONS) is False


def test_production_plan_lifecycle():
    """Verify ProductionPlan status flow."""
    assert validate_transition(ProductionPlanStatus.DRAFT, ProductionPlanStatus.PLANNED, ALLOWED_PRODUCTION_TRANSITIONS) is True
    assert validate_transition(ProductionPlanStatus.PLANNED, ProductionPlanStatus.FIRM, ALLOWED_PRODUCTION_TRANSITIONS) is True
    assert validate_transition(ProductionPlanStatus.FIRM, ProductionPlanStatus.RELEASED, ALLOWED_PRODUCTION_TRANSITIONS) is True
    assert validate_transition(ProductionPlanStatus.RELEASED, ProductionPlanStatus.IN_PROGRESS, ALLOWED_PRODUCTION_TRANSITIONS) is True
    assert validate_transition(ProductionPlanStatus.IN_PROGRESS, ProductionPlanStatus.COMPLETED, ALLOWED_PRODUCTION_TRANSITIONS) is True

    # Cannot skip from DRAFT straight to COMPLETED
    assert validate_transition(ProductionPlanStatus.DRAFT, ProductionPlanStatus.COMPLETED, ALLOWED_PRODUCTION_TRANSITIONS) is False


def test_shortage_lifecycle():
    """Verify Shortage status transitions."""
    assert validate_transition(ShortageStatus.DETECTED, ShortageStatus.ACKNOWLEDGED, ALLOWED_SHORTAGE_TRANSITIONS) is True
    assert validate_transition(ShortageStatus.ACKNOWLEDGED, ShortageStatus.MITIGATED, ALLOWED_SHORTAGE_TRANSITIONS) is True
    assert validate_transition(ShortageStatus.MITIGATED, ShortageStatus.RESOLVED, ALLOWED_SHORTAGE_TRANSITIONS) is True

    # Resolved cannot be re-detected without a new planning run
    assert validate_transition(ShortageStatus.RESOLVED, ShortageStatus.DETECTED, ALLOWED_SHORTAGE_TRANSITIONS) is False


def test_planning_run_lifecycle():
    """Verify PlanningRun states: QUEUED -> RUNNING -> COMPLETED."""
    assert validate_transition(PlanningRunStatus.QUEUED, PlanningRunStatus.RUNNING, ALLOWED_PLANNING_RUN_TRANSITIONS) is True
    assert validate_transition(PlanningRunStatus.RUNNING, PlanningRunStatus.COMPLETED, ALLOWED_PLANNING_RUN_TRANSITIONS) is True
    assert validate_transition(PlanningRunStatus.RUNNING, PlanningRunStatus.FAILED, ALLOWED_PLANNING_RUN_TRANSITIONS) is True

    # Completed runs cannot re-run
    assert validate_transition(PlanningRunStatus.COMPLETED, PlanningRunStatus.RUNNING, ALLOWED_PLANNING_RUN_TRANSITIONS) is False


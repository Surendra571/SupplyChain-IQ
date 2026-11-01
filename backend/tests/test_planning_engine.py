"""SupplyChain IQ - Comprehensive Test Suite for Phase 5 Supply-Demand Planning Engine.

Validates:
- Week-by-week Projected Available Balance (PAB) simulation
- Two shortage measures (Demand Shortage vs. Safety Stock Gap)
- 10 Business rules (period availability, delays, cancellations, duplicate prevention,
  reservations, supplier capacity, production capacity, UOM validation, snapshots, root causes)
- Shortage Prioritization algorithm (Critical, High, Medium, Low tiers)
- 8 Root cause diagnostic categories
- Normal, boundary, and failure cases
- 100% week-by-week balance reconciliation
"""

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import pytest

from backend.app.models.enums import (
    LocationType,
    PurchaseOrderStatus,
    ShipmentStatus,
    ShortageSeverity,
    SKUType,
)
from backend.app.planning.engine import SupplyDemandPlanningEngine, parse_week_bucket
from backend.app.planning.models import (
    PlanningConfig,
    PriorityTier,
    ShortageRootCause,
    WeeklyProjection,
)
from backend.app.planning.prioritization import ShortagePrioritizer
from backend.app.planning.root_cause import RootCauseAnalyzer
from backend.app.planning.snapshot import PlanningSnapshotManager


@pytest.fixture
def base_config():
    return PlanningConfig(horizon_weeks=4)


@pytest.fixture
def minimal_planning_data():
    """Deterministic synthetic fixture for unit testing specific SCM rules."""
    sku_id = "00000000-0000-0000-0000-000000000001"
    loc_id = "00000000-0000-0000-0000-000000000002"
    supp_id = "00000000-0000-0000-0000-000000000003"
    po_id = "00000000-0000-0000-0000-000000000004"

    return {
        "skus": [{
            "id": sku_id,
            "sku_code": "SKU-TEST-01",
            "name": "Test Finished Good",
            "category": "TEST",
            "sku_type": SKUType.FINISHED_GOOD.value,
            "unit_of_measure": "EA",
            "unit_cost": 50.0,
            "unit_price": 100.0,
        }],
        "locations": [{
            "id": loc_id,
            "location_code": "LOC-TEST-01",
            "name": "Central DC",
            "location_type": LocationType.DC.value,
            "capacity_units": 10000,
        }],
        "suppliers": [{
            "id": supp_id,
            "supplier_code": "SUP-TEST-01",
            "name": "Prime Supplier",
        }],
        "supplier_skus": [{
            "supplier_id": supp_id,
            "sku_id": sku_id,
            "lead_time_days": 14,
        }],
        "inventories": [{
            "sku_id": sku_id,
            "location_id": loc_id,
            "on_hand_qty": 200,
            "allocated_qty": 50,
            "safety_stock_qty": 100,
        }],
        "forecast_demands": [
            {"sku_id": sku_id, "location_id": loc_id, "week_bucket": "2026W01", "forecast_qty": 100},
            {"sku_id": sku_id, "location_id": loc_id, "week_bucket": "2026W02", "forecast_qty": 100},
            {"sku_id": sku_id, "location_id": loc_id, "week_bucket": "2026W03", "forecast_qty": 100},
            {"sku_id": sku_id, "location_id": loc_id, "week_bucket": "2026W04", "forecast_qty": 100},
        ],
        "purchase_orders": [{
            "id": po_id,
            "po_number": "PO-TEST-001",
            "supplier_id": supp_id,
            "status": PurchaseOrderStatus.PLACED.value,
        }],
        "purchase_order_lines": [{
            "id": "00000000-0000-0000-0000-000000000005",
            "po_id": po_id,
            "line_number": 1,
            "sku_id": sku_id,
            "destination_location_id": loc_id,
            "ordered_qty": 150,
            "received_qty": 0,
            "promised_delivery_date": "2026-01-08T00:00:00Z",  # Week 2 (2026W02)
            "unit_of_measure": "EA",
        }],
        "shipments": [],
        "production_plans": [],
        "supplier_capacities": [],
        "substitute_skus": [],
    }


# ===========================================================================
# 1. Core Calculations & Shortage Measures Tests
# ===========================================================================

def test_pab_calculation_and_reconciliation(minimal_planning_data, base_config):
    """Verify week-by-week PAB progression:

    PAB[0] = 200
    Week 1:
      Receipts = 0, ForecastDemand = 100, Allocations = 50 (reservation)
      AvailableBeforeDemand = 200 - 50 = 150
      ClosingPAB = 150 - 100 = 50
      SafetyStock = 100 -> SafetyStockGap = 100 - 50 = 50 (WARNING)
      DemandShortage = MAX(0, 100 - 150) = 0
    Week 2:
      OpeningPAB = 50, PO Receipts = 150, Allocations = 0, Demand = 100
      AvailableBeforeDemand = 50 + 150 = 200
      ClosingPAB = 200 - 100 = 100
      SafetyStock = 100 -> SafetyStockGap = 0, DemandShortage = 0
    """
    engine = SupplyDemandPlanningEngine(base_config)
    engine.load_data(minimal_planning_data)

    projections, shortages, summary = engine.run_planning(run_number=1, horizon_weeks=4)

    # 100% week-by-week balance reconciliation
    assert engine.verify_balance_reconciliation(projections) is True

    assert len(projections) == 4

    p_w1 = projections[0]
    assert p_w1.week_bucket == "2026W01"
    assert p_w1.opening_pab == 200
    assert p_w1.allocations == 50
    assert p_w1.available_before_demand == 150
    assert p_w1.closing_pab == 50
    assert p_w1.demand_shortage == 0
    assert p_w1.safety_stock_gap == 50

    p_w2 = projections[1]
    assert p_w2.week_bucket == "2026W02"
    assert p_w2.opening_pab == 50
    assert p_w2.purchase_receipts == 150
    assert p_w2.available_before_demand == 200
    assert p_w2.closing_pab == 100
    assert p_w2.demand_shortage == 0
    assert p_w2.safety_stock_gap == 0


def test_two_shortage_measures_critical_stockout(minimal_planning_data, base_config):
    """When AvailableBeforeDemand < ForecastDemand, ClosingPAB < 0.

    Verify DemandShortage = ForecastDemand - AvailableBeforeDemand
    and SafetyStockGap = SafetyStock - ClosingPAB.
    """
    # Set opening on-hand to 30, demand to 100 in week 1 with 0 allocations
    minimal_planning_data["inventories"][0]["on_hand_qty"] = 30
    minimal_planning_data["inventories"][0]["allocated_qty"] = 0
    minimal_planning_data["inventories"][0]["safety_stock_qty"] = 50

    engine = SupplyDemandPlanningEngine(base_config)
    engine.load_data(minimal_planning_data)

    projections, shortages, summary = engine.run_planning(run_number=1, horizon_weeks=2)

    p_w1 = projections[0]
    # AvailableBeforeDemand = 30
    # Demand = 100 -> ClosingPAB = -70
    assert p_w1.available_before_demand == 30
    assert p_w1.closing_pab == -70
    assert p_w1.demand_shortage == 70  # MAX(0, 100 - 30)
    assert p_w1.safety_stock_gap == 120  # MAX(0, 50 - (-70))

    # Shortage record created with CRITICAL severity
    w1_shortage = [s for s in shortages if s.week_bucket == "2026W01"][0]
    assert w1_shortage.severity == ShortageSeverity.CRITICAL
    assert w1_shortage.demand_shortage_qty == 70
    assert w1_shortage.safety_stock_gap_qty == 120
    assert w1_shortage.projected_deficit_qty == 120


# ===========================================================================
# 2. Business Rules Validation (Rules 1 to 8)
# ===========================================================================

def test_rule_1_count_inbound_in_available_period(minimal_planning_data, base_config):
    """Rule 1: Inbound receipts must only appear in the week they are expected."""
    # Move PO delivery date to 2026W03 (2026-01-15)
    minimal_planning_data["purchase_order_lines"][0]["promised_delivery_date"] = "2026-01-15T00:00:00Z"

    engine = SupplyDemandPlanningEngine(base_config)
    engine.load_data(minimal_planning_data)
    projections, _, _ = engine.run_planning(horizon_weeks=4)

    assert projections[0].purchase_receipts == 0  # 2026W01
    assert projections[1].purchase_receipts == 0  # 2026W02
    assert projections[2].purchase_receipts == 150  # 2026W03
    assert projections[3].purchase_receipts == 0  # 2026W04


def test_rule_2_delayed_shipment_uses_revised_eta(minimal_planning_data, base_config):
    """Rule 2: Delayed shipments must use revised arrival dates (shifting receipts)."""
    # PO was promised in 2026W02, but shipment ETA is delayed to 2026W04 (2026-01-22)
    po_id = minimal_planning_data["purchase_orders"][0]["id"]
    minimal_planning_data["shipments"] = [{
        "id": "00000000-0000-0000-0000-000000000009",
        "po_id": po_id,
        "carrier_code": "DHL",
        "tracking_number": "TRACK-DELAY-001",
        "status": ShipmentStatus.IN_TRANSIT.value,
        "eta": "2026-01-22T00:00:00Z",  # Week 4 (2026W04)
        "actual_delivery_date": None,
    }]

    engine = SupplyDemandPlanningEngine(base_config)
    engine.load_data(minimal_planning_data)
    projections, shortages, _ = engine.run_planning(horizon_weeks=4)

    # Inbound receipts should be 0 in week 2 and 150 in week 4
    assert projections[1].purchase_receipts == 0
    assert projections[3].purchase_receipts == 150

    # Shortage in week 2 should identify Transportation delay
    w2_shortage = [s for s in shortages if s.week_bucket == "2026W02"]
    if w2_shortage:
        assert w2_shortage[0].root_cause == ShortageRootCause.TRANSPORTATION_DELAY
        assert "TRACK-DELAY-001" in w2_shortage[0].root_cause_explanation


def test_rule_3_cancelled_purchase_orders_ignored(minimal_planning_data, base_config):
    """Rule 3: Cancelled purchase orders must not contribute to receipts."""
    minimal_planning_data["purchase_orders"][0]["status"] = PurchaseOrderStatus.CANCELLED.value

    engine = SupplyDemandPlanningEngine(base_config)
    engine.load_data(minimal_planning_data)
    projections, _, _ = engine.run_planning(horizon_weeks=4)

    # PO in week 2 is cancelled -> 0 receipts
    assert projections[1].purchase_receipts == 0


def test_rule_4_prevent_duplicate_receipt_counting(minimal_planning_data, base_config):
    """Rule 4: When a shipment exists for a PO line, receipts are not counted twice."""
    po_id = minimal_planning_data["purchase_orders"][0]["id"]
    minimal_planning_data["shipments"] = [{
        "id": "00000000-0000-0000-0000-000000000009",
        "po_id": po_id,
        "carrier_code": "FEDEX",
        "tracking_number": "TRACK-EXACT-001",
        "status": ShipmentStatus.IN_TRANSIT.value,
        "eta": "2026-01-08T00:00:00Z",  # Week 2 (same as PO line)
    }]

    engine = SupplyDemandPlanningEngine(base_config)
    engine.load_data(minimal_planning_data)
    projections, _, _ = engine.run_planning(horizon_weeks=4)

    # Receipts in week 2 must remain exactly 150, NOT 300
    assert projections[1].purchase_receipts == 150


def test_rule_5_respect_inventory_reservations(minimal_planning_data, base_config):
    """Rule 5: Reserved inventory cannot be consumed by general customer demand."""
    minimal_planning_data["inventories"][0]["on_hand_qty"] = 100
    minimal_planning_data["inventories"][0]["allocated_qty"] = 80
    minimal_planning_data["forecast_demands"][0]["forecast_qty"] = 50

    engine = SupplyDemandPlanningEngine(base_config)
    engine.load_data(minimal_planning_data)
    projections, _, _ = engine.run_planning(horizon_weeks=1)

    p = projections[0]
    # AvailableBeforeDemand = 100 - 80 = 20
    # ForecastDemand = 50 -> ClosingPAB = 20 - 50 = -30
    assert p.available_before_demand == 20
    assert p.closing_pab == -30
    assert p.demand_shortage == 30


def test_rule_6_supplier_capacity_exceeded_diagnosed(minimal_planning_data, base_config):
    """Rule 6: Supplier capacity ceiling constraint diagnosed in root cause."""
    supp_id = minimal_planning_data["suppliers"][0]["id"]
    sku_id = minimal_planning_data["skus"][0]["id"]

    # Record capacity constraint where committed > max + surge
    minimal_planning_data["supplier_capacities"] = [{
        "supplier_id": supp_id,
        "sku_id": sku_id,
        "week_bucket": "2026W03",
        "max_capacity_units": 100,
        "surge_capacity_units": 20,
        "committed_units": 200,  # Exceeded limit
    }]

    # Force deficit in week 3
    minimal_planning_data["inventories"][0]["on_hand_qty"] = 0
    minimal_planning_data["inventories"][0]["allocated_qty"] = 0

    engine = SupplyDemandPlanningEngine(base_config)
    engine.load_data(minimal_planning_data)
    _, shortages, _ = engine.run_planning(horizon_weeks=4)

    w3_shortages = [s for s in shortages if s.week_bucket == "2026W03"]
    assert any(s.root_cause == ShortageRootCause.SUPPLIER_CAPACITY_SHORTAGE for s in w3_shortages)


def test_rule_7_production_capacity_respected(minimal_planning_data, base_config):
    """Rule 7: Plant production output is capped to capacity and diagnosed."""
    sku_id = minimal_planning_data["skus"][0]["id"]
    loc_id = minimal_planning_data["locations"][0]["id"]

    # Plant capacity limit is 200
    minimal_planning_data["locations"][0]["capacity_units"] = 200

    # Scheduled production is 500 in week 2
    minimal_planning_data["production_plans"] = [{
        "sku_id": sku_id,
        "location_id": loc_id,
        "week_bucket": "2026W02",
        "planned_quantity": 500,
        "status": "PLANNED",
    }]

    engine = SupplyDemandPlanningEngine(base_config)
    engine.load_data(minimal_planning_data)
    projections, shortages, _ = engine.run_planning(horizon_weeks=2)

    # Feasible production receipts must be capped to 200
    assert projections[1].production_receipts == 200


def test_rule_8_unit_of_measure_mismatch_raises_error(minimal_planning_data, base_config):
    """Rule 8: Inbound order lines with mismatched UOM are rejected."""
    minimal_planning_data["purchase_order_lines"][0]["unit_of_measure"] = "BOX"  # Master is EA

    engine = SupplyDemandPlanningEngine(base_config)
    engine.load_data(minimal_planning_data)

    with pytest.raises(ValueError, match="Unit of measure mismatch"):
        engine.run_planning(horizon_weeks=2)


# ===========================================================================
# 3. Shortage Prioritization & Root Cause Coverage Tests
# ===========================================================================

def test_prioritization_scoring_tiers():
    """Verify prioritization formula produces Critical, High, Medium, and Low tiers."""
    prioritizer = ShortagePrioritizer()

    # 1. Critical Tier (immediate stockout, huge financial impact, FG, single source)
    score_crit, tier_crit, fin_crit, breakdown_crit = prioritizer.calculate_priority(
        days_until_stockout=0,
        shortage_qty=1000,
        avg_weekly_demand=100.0,
        unit_cost=100.0,
        unit_price=200.0,
        sku_type=SKUType.FINISHED_GOOD.value,
        location_type=LocationType.DC.value,
        lead_time_days=45,
        has_alternative_suppliers=False,
        has_active_substitute=False,
    )
    assert score_crit >= 75.0
    assert tier_crit == PriorityTier.CRITICAL
    assert fin_crit == 100000.0
    assert breakdown_crit["days_until_stockout_score"] == 100.0

    # 2. Low Tier (distant horizon, small quantity, cheap RM, multiple suppliers)
    score_low, tier_low, _, _ = prioritizer.calculate_priority(
        days_until_stockout=120,
        shortage_qty=5,
        avg_weekly_demand=500.0,
        unit_cost=0.50,
        unit_price=1.00,
        sku_type=SKUType.RAW_MATERIAL.value,
        location_type=LocationType.PLANT.value,
        lead_time_days=3,
        has_alternative_suppliers=True,
        has_active_substitute=True,
    )
    assert score_low < 25.0
    assert tier_low == PriorityTier.LOW


def test_root_cause_categories_full_coverage():
    """Verify all 8 root cause categories are correctly diagnosed by the engine."""
    analyzer = RootCauseAnalyzer(demand_spike_multiplier=1.5)

    # 1. Missing Lead Time
    cause, _ = analyzer.diagnose("SKU-1", "LOC-1", "2026W01", 1, 100, 100, 50, 100, missing_lead_time=True)
    assert cause == ShortageRootCause.MISSING_LEAD_TIME

    # 2. Invalid Substitute
    cause, _ = analyzer.diagnose("SKU-1", "LOC-1", "2026W01", 1, 100, 100, 50, 100, invalid_substitute=True)
    assert cause == ShortageRootCause.INVALID_SUBSTITUTE

    # 3. Transportation Delay
    cause, _ = analyzer.diagnose(
        "SKU-1", "LOC-1", "2026W01", 1, 100, 100, 50, 100,
        delayed_shipments=[{"tracking_number": "TRK-01"}]
    )
    assert cause == ShortageRootCause.TRANSPORTATION_DELAY

    # 4. Supplier Delay
    cause, _ = analyzer.diagnose(
        "SKU-1", "LOC-1", "2026W01", 1, 100, 100, 50, 100,
        delayed_pos=[{"po_number": "PO-01"}]
    )
    assert cause == ShortageRootCause.SUPPLIER_DELAY

    # 5. Supplier Capacity Shortage
    cause, _ = analyzer.diagnose(
        "SKU-1", "LOC-1", "2026W01", 1, 100, 100, 50, 100,
        supplier_capacity_exceeded={"max_capacity_units": 100, "committed_units": 200}
    )
    assert cause == ShortageRootCause.SUPPLIER_CAPACITY_SHORTAGE

    # 6. Production Constraint
    cause, _ = analyzer.diagnose(
        "SKU-1", "LOC-1", "2026W01", 1, 100, 100, 50, 100,
        production_constrained={"capacity_units": 50, "planned_units": 150}
    )
    assert cause == ShortageRootCause.PRODUCTION_CONSTRAINT

    # 7. Demand Spike (demand 300 vs avg 100)
    cause, _ = analyzer.diagnose("SKU-1", "LOC-1", "2026W05", 5, 300, 100, 50, 50)
    assert cause == ShortageRootCause.DEMAND_SPIKE

    # 8. Insufficient Opening Inventory (week 1, starting stock 10 < safety stock 50)
    cause, _ = analyzer.diagnose("SKU-1", "LOC-1", "2026W01", 1, 100, 100, 10, 50)
    assert cause == ShortageRootCause.INSUFFICIENT_OPENING_INVENTORY


# ===========================================================================
# 4. End-to-End Starter Dataset Execution & Persistence
# ===========================================================================

def test_starter_dataset_e2e_reconciliation(tmp_path):
    """Execute planning engine on generated starter dataset and verify full reconciliation."""
    data_dir = Path("data/generated/starter/csv")
    if not data_dir.exists():
        pytest.skip("Starter dataset CSVs not present on disk.")

    engine = SupplyDemandPlanningEngine.from_directory(data_dir, config=PlanningConfig(horizon_weeks=12))
    projections, shortages, summary = engine.run_planning(run_number=1, horizon_weeks=12)

    # 1. Total projections match SKU-location-week count
    assert len(projections) == 6000
    assert summary.total_shortages == len(shortages)
    assert summary.critical_shortages + summary.warning_shortages == summary.total_shortages

    # 2. Reconcile balances week-by-week
    assert engine.verify_balance_reconciliation(projections) is True

    # 3. Export snapshot files
    snapshot_mgr = PlanningSnapshotManager(tmp_path)
    run_dir = snapshot_mgr.export_snapshot_files(summary, projections, shortages)

    assert (run_dir / "summary.json").exists()
    assert (run_dir / "projections.csv").exists()
    assert (run_dir / "shortages.csv").exists()
    assert (run_dir / "shortages.json").exists()

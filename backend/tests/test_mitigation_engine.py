"""SupplyChain IQ - Comprehensive Test Suite for Phase 6 Mitigation Recommendation Engine.

Validates:
- All 7 mitigation option types:
  1. Existing supplier procurement
  2. Alternative approved supplier
  3. Expedited shipment
  4. Inventory transfer from another location
  5. Production increase
  6. Approved substitute SKU
  7. Partial fulfillment
- Feasibility constraints:
  - Supplier approval & expiration
  - Supplier capacity & MOQ
  - Lead time vs required date
  - Plant capacity & BOM component availability
  - Source safety stock preservation during transfers
  - Substitute approval & conversion
- Google OR-Tools MILP optimizer
- 4-way comparison engine (Cheapest, Fastest, Best Service, Recommended)
"""

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import pytest

from backend.app.models.enums import (
    LocationType,
    MitigationActionType,
    PurchaseOrderStatus,
    ShipmentStatus,
    ShortageSeverity,
    SKUType,
)
from backend.app.mitigation.comparison import ComparisonEngine
from backend.app.mitigation.generator import CandidateGenerator
from backend.app.mitigation.models import MitigationCandidate, MitigationConfig
from backend.app.mitigation.optimizer import MitigationOptimizer
from backend.app.mitigation.service import MitigationService
from backend.app.planning.models import PriorityTier, ShortageOutput, ShortageRootCause


@pytest.fixture
def sample_shortage():
    """Deterministic synthetic shortage fixture."""
    return ShortageOutput(
        business_id="SHORT-TEST-0001",
        planning_run_id="RUN-TEST-0001",
        sku_id="00000000-0000-0000-0000-000000000001",
        sku_code="SKU-FG-001",
        sku_name="Test Finished Good",
        location_id="00000000-0000-0000-0000-000000000002",
        location_code="LOC-DC-01",
        location_name="Distribution Center 1",
        week_bucket="2026W03",
        week_index=3,
        days_until_stockout=14,
        projected_deficit_qty=200,
        demand_shortage_qty=150,
        safety_stock_gap_qty=200,
        severity=ShortageSeverity.CRITICAL,
        priority_tier=PriorityTier.CRITICAL,
        priority_score=85.0,
        financial_impact=10000.0,
        root_cause=ShortageRootCause.SUPPLIER_DELAY,
        root_cause_explanation="Supplier delivery delayed.",
    )


@pytest.fixture
def mock_sc_data(sample_shortage):
    """Network dataset fixture with multi-tier sourcing, BOM, plants, and transfers."""
    sku_id = sample_shortage.sku_id
    loc_id = sample_shortage.location_id
    loc_other_id = "00000000-0000-0000-0000-000000000099"
    plant_id = "00000000-0000-0000-0000-000000000088"
    comp_sku_id = "00000000-0000-0000-0000-000000000077"
    sub_sku_id = "00000000-0000-0000-0000-000000000066"
    supp_primary_id = "00000000-0000-0000-0000-000000000055"
    supp_secondary_id = "00000000-0000-0000-0000-000000000044"
    po_id = "00000000-0000-0000-0000-000000000033"
    bom_id = "00000000-0000-0000-0000-000000000022"

    return {
        "skus": [
            {"id": sku_id, "sku_code": "SKU-FG-001", "sku_type": SKUType.FINISHED_GOOD.value, "unit_cost": 50.0, "unit_price": 100.0, "unit_of_measure": "EA"},
            {"id": comp_sku_id, "sku_code": "SKU-RM-001", "sku_type": SKUType.RAW_MATERIAL.value, "unit_cost": 10.0, "unit_price": 20.0, "unit_of_measure": "EA"},
            {"id": sub_sku_id, "sku_code": "SKU-SUB-001", "sku_type": SKUType.FINISHED_GOOD.value, "unit_cost": 55.0, "unit_price": 110.0, "unit_of_measure": "EA"},
        ],
        "locations": [
            {"id": loc_id, "location_code": "LOC-DC-01", "location_type": LocationType.DC.value, "capacity_units": 50000},
            {"id": loc_other_id, "location_code": "LOC-DC-02", "location_type": LocationType.DC.value, "capacity_units": 50000},
            {"id": plant_id, "location_code": "LOC-PL-01", "location_type": LocationType.PLANT.value, "capacity_units": 1000},
        ],
        "suppliers": [
            {"id": supp_primary_id, "supplier_code": "SUP-PRIM-01"},
            {"id": supp_secondary_id, "supplier_code": "SUP-SEC-01"},
        ],
        "supplier_skus": [
            # Primary supplier
            {"supplier_id": supp_primary_id, "sku_id": sku_id, "unit_price": 48.0, "moq": 50, "lead_time_days": 10, "is_preferred": True, "effective_from": "2025-01-01T00:00:00Z", "effective_to": None},
            # Secondary supplier (higher MOQ and cost, faster lead time)
            {"supplier_id": supp_secondary_id, "sku_id": sku_id, "unit_price": 55.0, "moq": 100, "lead_time_days": 7, "is_preferred": False, "effective_from": "2025-01-01T00:00:00Z", "effective_to": None},
        ],
        "supplier_capacities": [
            {"supplier_id": supp_primary_id, "sku_id": sku_id, "week_bucket": "2026W03", "max_capacity_units": 500, "surge_capacity_units": 100, "committed_units": 200},
            {"supplier_id": supp_secondary_id, "sku_id": sku_id, "week_bucket": "2026W03", "max_capacity_units": 1000, "surge_capacity_units": 200, "committed_units": 100},
        ],
        "inventories": [
            # Target location
            {"sku_id": sku_id, "location_id": loc_id, "on_hand_qty": 0, "allocated_qty": 0, "safety_stock_qty": 50},
            # Source DC with surplus
            {"sku_id": sku_id, "location_id": loc_other_id, "on_hand_qty": 500, "allocated_qty": 50, "safety_stock_qty": 100},
            # Substitute SKU at target location
            {"sku_id": sub_sku_id, "location_id": loc_id, "on_hand_qty": 300, "allocated_qty": 0, "safety_stock_qty": 50},
            # Component at Plant
            {"sku_id": comp_sku_id, "location_id": plant_id, "on_hand_qty": 1000, "allocated_qty": 0, "safety_stock_qty": 100},
        ],
        "lead_times": [
            {"origin_location_id": loc_other_id, "destination_location_id": loc_id, "transit_days": 3, "cost_per_unit": 1.50},
        ],
        "purchase_orders": [
            {"id": po_id, "po_number": "PO-OPEN-001", "supplier_id": supp_primary_id, "status": PurchaseOrderStatus.PLACED.value},
        ],
        "purchase_order_lines": [
            {"id": "POL-OPEN-01", "po_id": po_id, "sku_id": sku_id, "destination_location_id": loc_id, "ordered_qty": 300, "received_qty": 0, "promised_delivery_date": "2026-01-26T00:00:00Z", "unit_of_measure": "EA"},
        ],
        "substitute_skus": [
            {"primary_sku_id": sku_id, "substitute_sku_id": sub_sku_id, "conversion_factor": 1.0, "effective_from": "2025-01-01T00:00:00Z", "effective_to": None},
        ],
        "boms": [
            {"id": bom_id, "parent_sku_id": sku_id, "bom_version": "v1.0", "is_active": True},
        ],
        "bom_components": [
            {"bom_id": bom_id, "component_sku_id": comp_sku_id, "quantity_per_parent": 2.0, "scrap_percentage": 0.0},
        ],
    }


# ===========================================================================
# 1. Feasibility Constraint Unit Tests
# ===========================================================================

def test_supplier_approval_and_expiration(mock_sc_data, sample_shortage):
    """Unapproved or expired supplier contracts must be flagged as infeasible."""
    # Set supplier contract to expired in 2024
    mock_sc_data["supplier_skus"][0]["effective_to"] = "2024-12-31T00:00:00Z"

    gen = CandidateGenerator(mock_sc_data)
    candidates = gen.generate_candidates(sample_shortage, current_date=datetime(2026, 1, 1, tzinfo=timezone.utc))

    exist_supp = [c for c in candidates if c.action_type == MitigationActionType.EXISTING_SUPPLIER_PROCUREMENT][0]
    assert exist_supp.is_feasible is False
    assert any("expired" in r.lower() for r in exist_supp.infeasibility_reasons)


def test_supplier_capacity_exhausted(mock_sc_data, sample_shortage):
    """When supplier capacity is fully committed, procurement option must be infeasible."""
    # Commit all capacity
    mock_sc_data["supplier_capacities"][0]["committed_units"] = 600  # max 500 + surge 100

    gen = CandidateGenerator(mock_sc_data)
    candidates = gen.generate_candidates(sample_shortage, current_date=datetime(2026, 1, 1, tzinfo=timezone.utc))

    exist_supp = [c for c in candidates if c.action_type == MitigationActionType.EXISTING_SUPPLIER_PROCUREMENT][0]
    assert exist_supp.is_feasible is False
    assert any("exhausted" in r.lower() for r in exist_supp.infeasibility_reasons)


def test_moq_respected_and_enforced(mock_sc_data, sample_shortage):
    """MOQ must be satisfied; if available capacity < MOQ, option must be infeasible."""
    # Deficit is 200, MOQ is 500, but max capacity is only 400
    mock_sc_data["supplier_skus"][0]["moq"] = 500
    mock_sc_data["supplier_capacities"][0]["max_capacity_units"] = 300
    mock_sc_data["supplier_capacities"][0]["surge_capacity_units"] = 0
    mock_sc_data["supplier_capacities"][0]["committed_units"] = 0

    gen = CandidateGenerator(mock_sc_data)
    candidates = gen.generate_candidates(sample_shortage, current_date=datetime(2026, 1, 1, tzinfo=timezone.utc))

    exist_supp = [c for c in candidates if c.action_type == MitigationActionType.EXISTING_SUPPLIER_PROCUREMENT][0]
    assert exist_supp.is_feasible is False
    assert any("moq" in r.lower() or "minimum order quantity" in r.lower() for r in exist_supp.infeasibility_reasons)


def test_lead_time_exceeds_shortage_window(mock_sc_data, sample_shortage):
    """When supplier lead time finishes after the shortage period, option is infeasible."""
    # Shortage is in week 3 (approx 14 days out). Lead time 60 days misses requirement.
    mock_sc_data["supplier_skus"][0]["lead_time_days"] = 60

    gen = CandidateGenerator(mock_sc_data)
    candidates = gen.generate_candidates(sample_shortage, current_date=datetime(2026, 1, 1, tzinfo=timezone.utc))

    exist_supp = [c for c in candidates if c.action_type == MitigationActionType.EXISTING_SUPPLIER_PROCUREMENT][0]
    assert exist_supp.is_feasible is False
    assert any("lead time" in r.lower() for r in exist_supp.infeasibility_reasons)


def test_transfer_safety_stock_preservation(mock_sc_data, sample_shortage):
    """Inventory transfer must never breach the source location's safety stock buffer."""
    # Source DC has on-hand: 120, allocated: 0, safety_stock: 100 -> Surplus is only 20
    mock_sc_data["inventories"][1]["on_hand_qty"] = 120
    mock_sc_data["inventories"][1]["allocated_qty"] = 0
    mock_sc_data["inventories"][1]["safety_stock_qty"] = 100

    gen = CandidateGenerator(mock_sc_data)
    candidates = gen.generate_candidates(sample_shortage, current_date=datetime(2026, 1, 1, tzinfo=timezone.utc))

    trans_cands = [c for c in candidates if c.action_type == MitigationActionType.INVENTORY_TRANSFER]
    assert len(trans_cands) > 0
    # Recoverable quantity is strictly capped to source surplus (20 units), preserving 100 safety stock
    assert trans_cands[0].recoverable_quantity == 20
    assert trans_cands[0].is_feasible is True


def test_production_component_availability_constraint(mock_sc_data, sample_shortage):
    """Production increase is infeasible if required BOM components are missing."""
    # Deplete raw material component inventory to 0
    mock_sc_data["inventories"][3]["on_hand_qty"] = 0

    gen = CandidateGenerator(mock_sc_data)
    candidates = gen.generate_candidates(sample_shortage, current_date=datetime(2026, 1, 1, tzinfo=timezone.utc))

    prod_cands = [c for c in candidates if c.action_type == MitigationActionType.PRODUCTION_INCREASE]
    assert len(prod_cands) > 0
    assert prod_cands[0].is_feasible is False
    assert any("component" in r.lower() for r in prod_cands[0].infeasibility_reasons)


def test_unapproved_substitute_rejected(mock_sc_data, sample_shortage):
    """Candidate substitute SKU with expired approval must be rejected as infeasible."""
    # Expire substitute approval in 2025
    mock_sc_data["substitute_skus"][0]["effective_to"] = "2025-10-01T00:00:00Z"

    gen = CandidateGenerator(mock_sc_data)
    candidates = gen.generate_candidates(sample_shortage, current_date=datetime(2026, 1, 1, tzinfo=timezone.utc))

    sub_cands = [c for c in candidates if c.action_type == MitigationActionType.APPROVED_SUBSTITUTE_SKU]
    assert len(sub_cands) > 0
    assert sub_cands[0].is_feasible is False
    assert any("expired" in r.lower() for r in sub_cands[0].infeasibility_reasons)


# ===========================================================================
# 2. 4-Way Comparison Engine Tests
# ===========================================================================

def test_comparison_engine_cheapest_fastest_best_service(mock_sc_data, sample_shortage):
    """Verify ComparisonEngine correctly classifies cheapest, fastest, best service, and recommended."""
    gen = CandidateGenerator(mock_sc_data)
    candidates = gen.generate_candidates(sample_shortage, current_date=datetime(2026, 1, 1, tzinfo=timezone.utc))

    comp_engine = ComparisonEngine()
    comparison = comp_engine.compare_options(sample_shortage, candidates)

    assert comparison.recommended_option is not None
    assert comparison.recommended_option.is_feasible is True

    assert comparison.cheapest_option is not None
    assert comparison.fastest_option is not None
    assert comparison.best_service_option is not None

    # Fastest should have minimum recovery_time_days
    assert comparison.fastest_option.recovery_time_days <= comparison.recommended_option.recovery_time_days

    # Cheapest should have minimum total_cost
    assert comparison.cheapest_option.total_cost <= comparison.recommended_option.total_cost

    # Contextual reason must be present
    assert len(comparison.comparison_summary) > 20
    assert "Recommended" in comparison.comparison_summary


# ===========================================================================
# 3. Google OR-Tools Constrained Optimization Solver Tests
# ===========================================================================

def test_ortools_optimizer_feasibility_and_capacity_allocation(mock_sc_data, sample_shortage):
    """Google OR-Tools MILP solver must select feasible options without forcing infeasible ones."""
    gen = CandidateGenerator(mock_sc_data)
    candidates = gen.generate_candidates(sample_shortage, current_date=datetime(2026, 1, 1, tzinfo=timezone.utc))

    optimizer = MitigationOptimizer()
    selected_options, summary = optimizer.optimize_mitigations(
        planning_run_id="RUN-TEST-0001",
        shortages=[sample_shortage],
        candidate_options=candidates,
    )

    assert summary.solver_status in ("OPTIMAL", "FEASIBLE")
    assert len(selected_options) > 0

    # Every selected option MUST be feasible (Rule: Do not force an infeasible recommendation)
    for opt in selected_options:
        assert opt.is_feasible is True
        assert opt.recoverable_quantity > 0

    # Total recovered quantity cannot exceed shortage deficit
    total_alloc = sum(opt.recoverable_quantity for opt in selected_options)
    assert total_alloc <= sample_shortage.projected_deficit_qty


def test_ortools_zero_feasible_candidates_handling(mock_sc_data, sample_shortage):
    """When no feasible candidates exist, solver must return empty selection without crashing."""
    # Force all suppliers, inventory, plants, and open POs to 0 / unavailable
    mock_sc_data["supplier_skus"][0]["lead_time_days"] = 999
    mock_sc_data["supplier_skus"][1]["lead_time_days"] = 999
    mock_sc_data["inventories"][1]["on_hand_qty"] = 0
    mock_sc_data["inventories"][2]["on_hand_qty"] = 0
    mock_sc_data["inventories"][3]["on_hand_qty"] = 0
    mock_sc_data["purchase_order_lines"] = []
    mock_sc_data["locations"][2]["capacity_units"] = 0

    gen = CandidateGenerator(mock_sc_data)
    candidates = gen.generate_candidates(sample_shortage, current_date=datetime(2026, 1, 1, tzinfo=timezone.utc))

    optimizer = MitigationOptimizer()
    selected, summary = optimizer.optimize_mitigations(
        planning_run_id="RUN-TEST-0001",
        shortages=[sample_shortage],
        candidate_options=candidates,
    )

    assert len(selected) == 0
    assert summary.solver_status == "NO_FEASIBLE_OPTIONS"
    assert summary.mitigated_shortages == 0


# ===========================================================================
# 4. End-to-End Mitigation Service Execution & Persistence
# ===========================================================================

def test_mitigation_service_e2e_plan_and_export(mock_sc_data, sample_shortage, tmp_path):
    """Execute complete end-to-end mitigation pipeline and export snapshot artifacts."""
    service = MitigationService(mock_sc_data)
    comparisons, candidates, summary = service.generate_mitigation_plan(
        planning_run_id="RUN-TEST-0001",
        shortages=[sample_shortage],
        current_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    assert len(comparisons) == 1
    assert len(candidates) >= 5
    assert summary.total_shortages == 1

    # Export snapshots
    export_dir = service.export_mitigation_snapshots(tmp_path, comparisons, candidates, summary)

    assert (export_dir / "mitigation_candidates.csv").exists()
    assert (export_dir / "recommended_mitigations.csv").exists()
    assert (export_dir / "mitigation_comparisons.json").exists()
    assert (export_dir / "mitigation_summary.json").exists()

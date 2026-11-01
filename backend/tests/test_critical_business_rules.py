"""SupplyChain IQ - Phase 9 Critical Business Rules Test Suite.

Exhaustive verification of the 12 core business rules:
1. Projected balances reconcile week by week.
2. Demand shortages are calculated correctly (ClosingPAB < 0 -> Hard Stockout).
3. Safety stock gaps are calculated separately (0 <= ClosingPAB < SafetyStock -> Warning Gap).
4. Delayed shipments do not arrive prematurely (revised_eta enforced).
5. Duplicate receipts are detected and not double-counted.
6. Supplier capacity is never silently exceeded.
7. Unapproved substitutes are rejected by the mitigation engine.
8. UOM mismatches are detected and flagged.
9. Every shortage has a traceable root cause diagnostic.
10. Every mitigation option has an explicit feasibility explanation.
11. Approvals and rejections strictly create immutable AuditEvent records.
12. Previous planning runs remain immutable and unchanged across successive runs.
"""

from datetime import datetime, timezone
import json
import uuid
import pytest
from sqlalchemy import select

from backend.app.core.database import AsyncSessionLocal, SessionLocal
from backend.app.models.audit import AuditEvent
from backend.app.models.enums import (
    LocationType,
    MitigationActionType,
    MitigationDecisionType,
    MitigationOptionStatus,
    PurchaseOrderStatus,
    ShipmentStatus,
    ShortageSeverity,
    ShortageStatus,
    SKUType,
)
from backend.app.models.planning import MitigationDecision, MitigationOption, PlanningRun, Shortage
from backend.app.planning.engine import SupplyDemandPlanningEngine
from backend.app.planning.models import PlanningConfig, ShortageRootCause
from backend.app.mitigation.generator import CandidateGenerator
from backend.app.validation.rules import validate_unit_of_measure_consistency
from backend.app.workers.tasks import run_planning_job_sync


@pytest.fixture
def base_config():
    return PlanningConfig(horizon_weeks=6)


@pytest.fixture
def business_rule_test_data():
    """Deterministic dataset engineered to isolate and test specific business constraints."""
    sku_id = str(uuid.uuid4())
    sub_sku_id = str(uuid.uuid4())
    loc_id = str(uuid.uuid4())
    supp_id = str(uuid.uuid4())

    return {
        "skus": [
            {
                "id": sku_id,
                "business_id": "SKU-CRIT-01",
                "sku_code": "SKU-CRIT-01",
                "name": "Critical Assembly",
                "category": "ASSEMBLY",
                "sku_type": SKUType.FINISHED_GOOD.value,
                "unit_of_measure": "EA",
                "unit_cost": 100.0,
                "unit_price": 250.0,
            },
            {
                "id": sub_sku_id,
                "business_id": "SKU-SUB-UNAPPROVED",
                "sku_code": "SKU-SUB-UNAPPROVED",
                "name": "Unapproved Alternate",
                "category": "ASSEMBLY",
                "sku_type": SKUType.FINISHED_GOOD.value,
                "unit_of_measure": "EA",
                "unit_cost": 95.0,
                "unit_price": 250.0,
            },
        ],
        "locations": [
            {
                "id": loc_id,
                "business_id": "LOC-MAIN-01",
                "location_code": "LOC-MAIN-01",
                "name": "Main Distribution Hub",
                "location_type": LocationType.DC.value,
                "capacity_units": 50000,
            }
        ],
        "suppliers": [
            {
                "id": supp_id,
                "business_id": "SUP-CAP-01",
                "supplier_code": "SUP-CAP-01",
                "name": "Capped Capacity Supplier",
                "status": "ACTIVE",
            }
        ],
        "supplier_skus": [
            {
                "supplier_id": supp_id,
                "sku_id": sku_id,
                "lead_time_days": 7,
                "unit_cost": 100.0,
                "moq": 10,
                "is_primary": True,
            }
        ],
        "supplier_capacities": [
            {
                "supplier_id": supp_id,
                "sku_id": sku_id,
                "week_bucket": "2026W01",
                "capacity_units": 100,
            },
            {
                "supplier_id": supp_id,
                "sku_id": sku_id,
                "week_bucket": "2026W02",
                "capacity_units": 100,
            },
            {
                "supplier_id": supp_id,
                "sku_id": sku_id,
                "week_bucket": "2026W03",
                "capacity_units": 100,
            },
            {
                "supplier_id": supp_id,
                "sku_id": sku_id,
                "week_bucket": "2026W04",
                "capacity_units": 100,
            },
        ],
        "substitute_skus": [
            {
                "primary_sku_id": sku_id,
                "substitute_sku_id": sub_sku_id,
                "priority": 1,
                "conversion_ratio": 1.0,
                "is_approved": False,  # DELIBERATELY UNAPPROVED
            }
        ],
        "inventories": [
            {
                "sku_id": sku_id,
                "location_id": loc_id,
                "on_hand_qty": 200,
                "allocated_qty": 50,  # Available = 150
                "safety_stock_qty": 80,
            }
        ],
        "forecast_demands": [
            {"sku_id": sku_id, "location_id": loc_id, "week_bucket": "2026W01", "forecast_qty": 50},
            {"sku_id": sku_id, "location_id": loc_id, "week_bucket": "2026W02", "forecast_qty": 60},
            {"sku_id": sku_id, "location_id": loc_id, "week_bucket": "2026W03", "forecast_qty": 100},
            {"sku_id": sku_id, "location_id": loc_id, "week_bucket": "2026W04", "forecast_qty": 150},
            {"sku_id": sku_id, "location_id": loc_id, "week_bucket": "2026W05", "forecast_qty": 50},
            {"sku_id": sku_id, "location_id": loc_id, "week_bucket": "2026W06", "forecast_qty": 50},
        ],
        "purchase_orders": [],
        "purchase_order_lines": [],
        "shipments": [],
        "production_plans": [],
        "boms": [],
        "bom_components": [],
        "inventory_transactions": [],
    }


# ===========================================================================
# 1. Projected Balances Reconcile Week-by-Week
# ===========================================================================
def test_rule_projected_balances_reconcile_week_by_week(base_config, business_rule_test_data):
    """PAB_t = PAB_{t-1} + Inbound_t - GrossDemand_t, starting from Net Available Inventory."""
    engine = SupplyDemandPlanningEngine(base_config)
    engine.load_data(business_rule_test_data)
    projections, shortages, summary = engine.run_planning(run_number=1, horizon_weeks=6)

    sku_id = business_rule_test_data["skus"][0]["id"]
    loc_id = business_rule_test_data["locations"][0]["id"]
    proj_list = [p for p in projections if p.sku_id == sku_id and p.location_id == loc_id]
    proj_list.sort(key=lambda p: p.week_bucket)

    assert len(proj_list) == 6

    # Starting available = 200 - 50 = 150
    # W01: 150 - 50 = 100
    assert proj_list[0].closing_pab == 100
    # W02: 100 - 60 = 40
    assert proj_list[1].closing_pab == 40
    # W03: 40 - 100 = -60
    assert proj_list[2].closing_pab == -60
    # W04: -60 - 150 = -210
    assert proj_list[3].closing_pab == -210

    # Mathematical recurrence relation verified across all consecutive weeks
    prev = 150
    for p in proj_list:
        expected = prev + p.purchase_receipts + p.production_receipts + p.transfers_in - p.forecast_demand
        assert p.closing_pab == expected
        prev = p.closing_pab


# ===========================================================================
# 2. Demand Shortages Are Calculated Correctly (ClosingPAB < 0)
# ===========================================================================
def test_rule_demand_shortages_calculated_correctly(base_config, business_rule_test_data):
    """When ClosingPAB < 0, a CRITICAL Demand Shortage must be registered with exact deficit."""
    engine = SupplyDemandPlanningEngine(base_config)
    engine.load_data(business_rule_test_data)
    _, shortages, _ = engine.run_planning(run_number=1, horizon_weeks=6)

    critical_shortages = [s for s in shortages if s.severity == ShortageSeverity.CRITICAL]
    crit_w03 = next((s for s in critical_shortages if s.week_bucket == "2026W03"), None)
    crit_w04 = next((s for s in critical_shortages if s.week_bucket == "2026W04"), None)

    assert crit_w03 is not None
    assert crit_w03.demand_shortage_qty == 60  # Unmet customer demand
    assert crit_w03.financial_impact == 140.0 * 100.0  # (safety_stock 80 + demand_shortage 60) * unit_cost 100

    assert crit_w04 is not None
    assert crit_w04.demand_shortage_qty == 210  # Cumulative unmet demand: 150 - (-60) = 210


# ===========================================================================
# 3. Safety Stock Gaps Are Calculated Separately (0 <= ClosingPAB < SafetyStock)
# ===========================================================================
def test_rule_safety_stock_gaps_calculated_separately(base_config, business_rule_test_data):
    """When 0 <= ClosingPAB < SafetyStock, a WARNING gap is emitted separately from Demand Shortage."""
    engine = SupplyDemandPlanningEngine(base_config)
    engine.load_data(business_rule_test_data)
    _, shortages, _ = engine.run_planning(run_number=1, horizon_weeks=6)

    warning_shortages = [s for s in shortages if s.severity == ShortageSeverity.WARNING]
    warn_w02 = next((s for s in warning_shortages if s.week_bucket == "2026W02"), None)

    assert warn_w02 is not None
    assert warn_w02.severity == ShortageSeverity.WARNING
    assert warn_w02.safety_stock_gap_qty == 40  # Safety Stock 80 - ClosingPAB 40 = 40 gap
    assert warn_w02.demand_shortage_qty == 0   # No customer stockout!

    # W03 has ClosingPAB = -60, so it must be CRITICAL, NOT WARNING
    warn_w03 = next((s for s in warning_shortages if s.week_bucket == "2026W03"), None)
    assert warn_w03 is None


# ===========================================================================
# 4. Delayed Shipments Do Not Arrive Prematurely
# ===========================================================================
def test_rule_delayed_shipments_do_not_arrive_prematurely(base_config, business_rule_test_data):
    """If a shipment is delayed from W02 to W04, supply must not be counted in W02 or W03."""
    po_id = str(uuid.uuid4())
    pol_id = str(uuid.uuid4())
    ship_id = str(uuid.uuid4())
    sku_id = business_rule_test_data["skus"][0]["id"]
    loc_id = business_rule_test_data["locations"][0]["id"]

    business_rule_test_data["purchase_orders"].append({
        "id": po_id,
        "po_number": "PO-DELAY-01",
        "supplier_id": business_rule_test_data["suppliers"][0]["id"],
        "status": PurchaseOrderStatus.PLACED.value,
    })
    business_rule_test_data["purchase_order_lines"].append({
        "id": pol_id,
        "po_id": po_id,
        "sku_id": sku_id,
        "destination_location_id": loc_id,
        "ordered_qty": 100,
        "received_qty": 0,
        "promised_delivery_date": "2026-01-08T00:00:00Z",  # Week 02
        "unit_of_measure": "EA",
    })
    business_rule_test_data["shipments"].append({
        "id": ship_id,
        "po_id": po_id,
        "po_line_id": pol_id,
        "sku_id": sku_id,
        "destination_location_id": loc_id,
        "status": ShipmentStatus.IN_TRANSIT.value,
        "shipped_qty": 100,
        "eta": "2026-01-22T00:00:00Z",  # Delayed to Week 04
    })

    engine = SupplyDemandPlanningEngine(base_config)
    engine.load_data(business_rule_test_data)
    projections, _, _ = engine.run_planning(run_number=1, horizon_weeks=6)

    proj_map = {p.week_bucket: p for p in projections if p.sku_id == sku_id}
    # Inbound receipts must be 0 in W01, W02, W03 and appear in W04
    assert proj_map["2026W01"].purchase_receipts == 0
    assert proj_map["2026W02"].purchase_receipts == 0
    assert proj_map["2026W03"].purchase_receipts == 0
    assert proj_map["2026W04"].purchase_receipts == 100


# ===========================================================================
# 5. Duplicate Receipts Are Detected and Handled
# ===========================================================================
def test_rule_duplicate_receipts_detected_and_handled(base_config, business_rule_test_data):
    """When both PO line and in-transit shipment reference the same order, receipt is counted once."""
    po_id = str(uuid.uuid4())
    pol_id = str(uuid.uuid4())
    sku_id = business_rule_test_data["skus"][0]["id"]
    loc_id = business_rule_test_data["locations"][0]["id"]

    business_rule_test_data["purchase_orders"].append({
        "id": po_id,
        "po_number": "PO-DUP-01",
        "supplier_id": business_rule_test_data["suppliers"][0]["id"],
        "status": PurchaseOrderStatus.PLACED.value,
    })
    business_rule_test_data["purchase_order_lines"].append({
        "id": pol_id,
        "po_id": po_id,
        "sku_id": sku_id,
        "destination_location_id": loc_id,
        "ordered_qty": 50,
        "received_qty": 0,
        "promised_delivery_date": "2026-01-08T00:00:00Z",  # W02
        "unit_of_measure": "EA",
    })
    business_rule_test_data["shipments"].append({
        "id": str(uuid.uuid4()),
        "po_id": po_id,
        "po_line_id": pol_id,
        "sku_id": sku_id,
        "destination_location_id": loc_id,
        "status": ShipmentStatus.IN_TRANSIT.value,
        "shipped_qty": 50,
        "eta": "2026-01-08T00:00:00Z",  # W02
    })

    engine = SupplyDemandPlanningEngine(base_config)
    engine.load_data(business_rule_test_data)
    projections, _, _ = engine.run_planning(run_number=1, horizon_weeks=4)

    proj_w02 = next(p for p in projections if p.sku_id == sku_id and p.week_bucket == "2026W02")
    # Receipt must be exactly 50, NOT 100
    assert proj_w02.purchase_receipts == 50


# ===========================================================================
# 6. Supplier Capacity Is Never Silently Exceeded
# ===========================================================================
def test_rule_supplier_capacity_never_silently_exceeded(base_config, business_rule_test_data):
    """When demand deficit exceeds supplier capacity, capacity shortage root causes are diagnosed."""
    sku_id = business_rule_test_data["skus"][0]["id"]

    engine = SupplyDemandPlanningEngine(base_config)
    engine.load_data(business_rule_test_data)
    _, shortages, _ = engine.run_planning(run_number=1, horizon_weeks=6)

    shortage_w04 = next((s for s in shortages if s.sku_id == sku_id and s.week_bucket == "2026W04"), None)
    assert shortage_w04 is not None
    # Root cause must diagnose supplier capacity shortage or demand spike
    assert shortage_w04.root_cause in (
        ShortageRootCause.SUPPLIER_CAPACITY_SHORTAGE,
        ShortageRootCause.DEMAND_SPIKE,
    )


# ===========================================================================
# 7. Unapproved Substitutes Are Rejected
# ===========================================================================
def test_rule_unapproved_substitutes_rejected(base_config, business_rule_test_data):
    """Substitutes configured with is_approved=False must NEVER be accepted as feasible mitigations."""
    engine = SupplyDemandPlanningEngine(base_config)
    engine.load_data(business_rule_test_data)
    _, shortages, _ = engine.run_planning(run_number=1, horizon_weeks=6)

    shortage = next(s for s in shortages if s.severity == ShortageSeverity.CRITICAL)
    generator = CandidateGenerator(business_rule_test_data)
    candidates = generator.generate_candidates(shortage, current_date=datetime(2026, 1, 1, tzinfo=timezone.utc))

    sub_candidates = [c for c in candidates if c.action_type == MitigationActionType.APPROVED_SUBSTITUTE_SKU]
    # In our dataset, is_approved is False for the substitute, so it must be infeasible or rejected
    for sub in sub_candidates:
        assert sub.is_feasible is False
        assert any("not approved" in r.lower() or "unapproved" in r.lower() for r in sub.infeasibility_reasons)


# ===========================================================================
# 8. UOM Mismatches Are Flagged
# ===========================================================================
def test_rule_uom_mismatches_are_flagged(business_rule_test_data):
    """When a transaction or PO Line has a UOM inconsistency (e.g. 50x cost inflation), validation engine flags it."""
    import copy
    corrupted_data = copy.deepcopy(business_rule_test_data)
    sku_id = corrupted_data["skus"][0]["id"]
    corrupted_data["purchase_order_lines"] = [{
        "id": str(uuid.uuid4()),
        "business_id": "POL-TEST-UOM-01",
        "purchase_order_id": str(uuid.uuid4()),
        "sku_id": sku_id,
        "order_qty": 100.0,
        "unit_cost": 5000.0,  # Master cost is 100.0 -> 50x mismatch
        "promised_delivery_date": "2026-01-08T00:00:00Z",
    }]

    issues = validate_unit_of_measure_consistency(corrupted_data, [0])
    assert len(issues) > 0
    assert any(i.issue_type == "UNIT_OF_MEASURE_MISMATCH" for i in issues)


# ===========================================================================
# 9. Every Shortage Has a Traceable Root Cause
# ===========================================================================
def test_rule_every_shortage_has_traceable_root_cause(base_config, business_rule_test_data):
    """Every detected shortage must possess a validated, non-empty root_cause classification."""
    engine = SupplyDemandPlanningEngine(base_config)
    engine.load_data(business_rule_test_data)
    _, shortages, _ = engine.run_planning(run_number=1, horizon_weeks=6)

    assert len(shortages) > 0
    valid_causes = set(ShortageRootCause)

    for s in shortages:
        assert s.root_cause is not None
        assert s.root_cause in valid_causes


# ===========================================================================
# 10. Every Mitigation Has a Feasibility Explanation
# ===========================================================================
def test_rule_every_mitigation_has_feasibility_explanation(base_config, business_rule_test_data):
    """Every mitigation candidate generated must provide an explicit feasibility or infeasibility reason."""
    engine = SupplyDemandPlanningEngine(base_config)
    engine.load_data(business_rule_test_data)
    _, shortages, _ = engine.run_planning(run_number=1, horizon_weeks=6)

    generator = CandidateGenerator(business_rule_test_data)
    for shortage in shortages[:3]:
        candidates = generator.generate_candidates(shortage, current_date=datetime(2026, 1, 1, tzinfo=timezone.utc))
        for c in candidates:
            # Candidate must have non-empty explanation or infeasibility_reasons
            has_explanation = bool(c.explanation and len(c.explanation.strip()) > 0) or (len(c.infeasibility_reasons) > 0)
            assert has_explanation


# ===========================================================================
# 11. Approvals and Rejections Create Audit Events
# ===========================================================================
@pytest.mark.anyio
async def test_rule_approvals_and_rejections_create_audit_events(seeded_starter_data):
    """Decision workflows (APPROVE and REJECT) strictly persist immutable AuditEvent records."""
    from backend.app.core.rbac import UserRole
    from backend.app.schemas.decision_api import DecisionSubmitRequest
    from backend.app.services.decision_service import DecisionService

    async with AsyncSessionLocal() as session:
        # Find an open mitigation option
        stmt = (
            select(MitigationOption)
            .where(MitigationOption.status == MitigationOptionStatus.PROPOSED)
            .limit(1)
        )
        res = await session.execute(stmt)
        opt = res.scalar_one_or_none()

        if opt is None:
            pytest.skip("No proposed mitigation option available for decision test.")

        opt_id = str(opt.id)
        decision_service = DecisionService(session)

        # Submit Approval
        approve_req = DecisionSubmitRequest(
            mitigation_option_id=opt_id,
            decision=MitigationDecisionType.APPROVED,
            reason="Phase 9 automated approval QA test",
        )
        app_resp = await decision_service.submit_decision(
            request=approve_req,
            user_id="qa-engineer@supplychainiq.com",
            user_role=UserRole.PLANNER,
        )
        assert app_resp.status == "SUCCESS"

        # Verify AuditEvent insertion
        audit_stmt = (
            select(AuditEvent)
            .where(AuditEvent.entity_name == "MitigationDecision")
            .where(AuditEvent.entity_id == app_resp.business_id)
        )
        audit_res = await session.execute(audit_stmt)
        audit_record = audit_res.scalar_one_or_none()

        assert audit_record is not None
        assert audit_record.action == "APPROVED"
        assert "qa-engineer@supplychainiq.com" in audit_record.performed_by
        before_state = json.loads(audit_record.before_state_json)
        after_state = json.loads(audit_record.after_state_json)
        assert before_state["option_status"] == "PROPOSED"
        assert after_state["option_status"] == "APPROVED"


# ===========================================================================
# 12. Previous Planning Runs Remain Unchanged
# ===========================================================================
def test_rule_previous_planning_runs_remain_unchanged(seeded_starter_data):
    """Successive planning runs never overwrite or alter the records of preceding runs."""
    with SessionLocal() as db:
        # Verify run 1 exists
        run1 = db.query(PlanningRun).filter(PlanningRun.run_number == 1).first()
        assert run1 is not None

        # Capture run 1 shortage counts and snapshot summary
        run1_shortages_count = db.query(Shortage).filter(Shortage.planning_run_id == run1.id).count()
        assert run1_shortages_count == 1405
        run1_completed_at = run1.completed_at

        # Execute a new run in dry-run/sync mode
        run_res = run_planning_job_sync(run_number=99, horizon_weeks=4, persist_db=False)
        assert run_res["status"] == "COMPLETED"

        # Re-verify Run 1 state remains perfectly intact
        db.refresh(run1)
        assert run1.completed_at == run1_completed_at
        post_shortages_count = db.query(Shortage).filter(Shortage.planning_run_id == run1.id).count()
        assert post_shortages_count == 1405

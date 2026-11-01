"""SupplyChain IQ - Automated Unit & Integration Tests for Validation Engine & Evaluation Module."""

import copy
import json
from pathlib import Path
import tempfile
import pytest

from backend.app.generator.anomalies import AnomalyInjector
from backend.app.generator.config import GeneratorConfig
from backend.app.generator.core import SyntheticDataGenerator
from backend.app.validation.engine import ValidationEngine
from backend.app.validation.evaluation import EvaluationModule
from backend.app.validation.models import ValidationCategory, ValidationSeverity
from backend.app.validation.reporter import ValidationReporter
from backend.app.validation.rules import (
    validate_date_ordering,
    validate_duplicate_receipts,
    validate_enums,
    validate_foreign_key_integrity,
    validate_inventory_transaction_reconciliation,
    validate_lifecycle_transitions,
    validate_primary_key_uniqueness,
    validate_quantity_reconciliation,
    validate_required_fields,
    validate_substitute_approval,
    validate_supplier_capacity,
    validate_unit_of_measure_consistency,
)


@pytest.fixture(scope="module")
def baseline_dataset():
    """Generate a clean starter baseline dataset for validation testing."""
    cfg = GeneratorConfig(seed=20261022, scale_name="starter")
    gen = SyntheticDataGenerator(cfg)
    return gen.generate_all()


# =============================================================================
# 1. Primary Key Uniqueness Tests
# =============================================================================
def test_category_01_primary_key_uniqueness(baseline_dataset):
    data = copy.deepcopy(baseline_dataset)
    # Inject duplicate PK
    dup_sku = copy.deepcopy(data["skus"][0])
    dup_sku["business_id"] = "SKU-DUP-TEST"
    data["skus"].append(dup_sku)

    issues = validate_primary_key_uniqueness(data, [0])
    assert any(i.issue_type == "DUPLICATE_PRIMARY_KEY" for i in issues)
    assert any(i.category == ValidationCategory.PRIMARY_KEY_UNIQUENESS.value for i in issues)


# =============================================================================
# 2. Foreign Key Integrity Tests
# =============================================================================
def test_category_02_foreign_key_integrity(baseline_dataset):
    data = copy.deepcopy(baseline_dataset)
    # Inject orphaned inventory SKU
    data["inventories"].append({
        "id": "ffffffff-ffff-ffff-ffff-ffffffffffff",
        "business_id": "INV-ORPHAN",
        "sku_id": "00000000-0000-0000-0000-000000000000",  # non-existent
        "location_id": data["locations"][0]["id"],
        "on_hand_qty": 100,
        "safety_stock_qty": 20,
    })

    issues = validate_foreign_key_integrity(data, [0])
    assert any(i.issue_type == "FOREIGN_KEY_VIOLATION" and i.record_id == "INV-ORPHAN" for i in issues)


# =============================================================================
# 3. Required Field Validation Tests
# =============================================================================
def test_category_03_required_fields(baseline_dataset):
    data = copy.deepcopy(baseline_dataset)
    # Remove required name
    data["skus"][0]["name"] = ""

    issues = validate_required_fields(data, [0])
    assert any(i.issue_type == "MISSING_REQUIRED_FIELD" and "name" in i.detection_rule.lower() for i in issues)


# =============================================================================
# 4. Enum Validation Tests
# =============================================================================
def test_category_04_enums(baseline_dataset):
    data = copy.deepcopy(baseline_dataset)
    # Corrupt sku_type
    data["skus"][0]["sku_type"] = "INVALID_TYPE_XYZ"

    issues = validate_enums(data, [0])
    assert any(i.issue_type == "INVALID_ENUM_VALUE" for i in issues)


# =============================================================================
# 5. Date Ordering Tests (Including ANOM-004)
# =============================================================================
def test_category_05_date_ordering_and_lead_time_anomaly(baseline_dataset):
    data = copy.deepcopy(baseline_dataset)
    # Invert shipment eta < etd
    data["shipments"][0]["etd"] = "2026-02-10T00:00:00+00:00"
    data["shipments"][0]["eta"] = "2026-02-01T00:00:00+00:00"

    # Inject past-due delivery date (ANOM-004)
    data["purchase_order_lines"][0]["promised_delivery_date"] = "2025-12-01T00:00:00+00:00"

    issues = validate_date_ordering(data, [0])
    assert any(i.issue_type == "DATE_ORDERING_VIOLATION" and i.entity_type == "shipments" for i in issues)
    assert any(i.issue_type == "SHORTAGE_CALCULATED_WITHOUT_LEAD_TIME" for i in issues)


# =============================================================================
# 6. Quantity Reconciliation Tests
# =============================================================================
def test_category_06_quantity_reconciliation(baseline_dataset):
    data = copy.deepcopy(baseline_dataset)
    # Negative on_hand_qty
    data["inventories"][0]["on_hand_qty"] = -50
    # Over-delivery
    data["purchase_order_lines"][0]["ordered_qty"] = 100
    data["purchase_order_lines"][0]["received_qty"] = 150

    issues = validate_quantity_reconciliation(data, [0])
    assert any(i.issue_type == "NEGATIVE_INVENTORY" for i in issues)
    assert any(i.issue_type == "OVER_DELIVERY_VIOLATION" for i in issues)


# =============================================================================
# 7. Unit of Measure Consistency Tests (Detects ANOM-005)
# =============================================================================
def test_category_07_unit_of_measure_consistency(baseline_dataset):
    data = copy.deepcopy(baseline_dataset)
    # Inflate unit cost by 50x (ANOM-005)
    line = data["purchase_order_lines"][0]
    line["unit_cost"] = line["unit_cost"] * 50.0

    issues = validate_unit_of_measure_consistency(data, [0])
    assert any(i.issue_type == "UNIT_OF_MEASURE_MISMATCH" and i.record_id == line["business_id"] for i in issues)


# =============================================================================
# 8. Supplier Capacity Tests (Detects ANOM-003)
# =============================================================================
def test_category_08_supplier_capacity(baseline_dataset):
    data = copy.deepcopy(baseline_dataset)
    # Exceed capacity
    cap = data["supplier_capacities"][0]
    cap["committed_units"] = cap["max_capacity_units"] + cap["surge_capacity_units"] + 5000

    issues = validate_supplier_capacity(data, [0])
    assert any(i.issue_type == "SUPPLIER_CAPACITY_EXCEEDED" and i.record_id == cap["business_id"] for i in issues)


# =============================================================================
# 9. Duplicate Receipt Detection Tests (Detects ANOM-001)
# =============================================================================
def test_category_09_duplicate_receipts(baseline_dataset):
    data = copy.deepcopy(baseline_dataset)
    inv = data["inventories"][0]
    # Add duplicate transaction
    data["inventory_transactions"].append({
        "id": "11111111-1111-1111-1111-111111111111",
        "business_id": "TXN-DUP-TEST",
        "sku_id": inv["sku_id"],
        "location_id": inv["location_id"],
        "transaction_type": "RECEIPT",
        "quantity": 500,
        "balance_after": inv["on_hand_qty"] + 500,
        "reference_id": "PO-DUPLICATE-POSTING",
        "notes": "Inbound inventory counted twice",
        "created_at": inv["created_at"],
    })

    issues = validate_duplicate_receipts(data, [0])
    assert any(i.issue_type == "INBOUND_INVENTORY_COUNTED_TWICE" and i.record_id == inv["business_id"] for i in issues)


# =============================================================================
# 10. Substitute Approval Validation Tests (Detects ANOM-002)
# =============================================================================
def test_category_10_substitute_approval(baseline_dataset):
    data = copy.deepcopy(baseline_dataset)
    sub = data["substitute_skus"][0]
    sub["effective_to"] = "2025-12-31T23:59:59+00:00"  # expired

    issues = validate_substitute_approval(data, [0])
    assert any(i.issue_type == "SUBSTITUTE_SKU_NOT_APPROVED" and i.record_id == sub["business_id"] for i in issues)


# =============================================================================
# 11. Lifecycle Transition Validation Tests
# =============================================================================
def test_category_11_lifecycle_transitions(baseline_dataset):
    data = copy.deepcopy(baseline_dataset)
    # Set PO to DRAFT but record received_qty > 0 on line
    draft_po = data["purchase_orders"][0]
    draft_po["status"] = "DRAFT"
    for line in data["purchase_order_lines"]:
        if line["po_id"] == draft_po["id"]:
            line["received_qty"] = 50
            break

    issues = validate_lifecycle_transitions(data, [0])
    assert any(i.issue_type == "INVALID_LIFECYCLE_STATE" for i in issues)


# =============================================================================
# 12. Inventory Transaction Reconciliation Tests
# =============================================================================
def test_category_12_inventory_transaction_reconciliation(baseline_dataset):
    data = copy.deepcopy(baseline_dataset)
    # Artificially alter physical inventory so it deviates from ledger
    data["inventories"][0]["on_hand_qty"] += 9999

    issues = validate_inventory_transaction_reconciliation(data, [0])
    assert any(i.issue_type == "INVENTORY_BALANCE_MISMATCH" for i in issues)


# =============================================================================
# End-to-End Integration Tests: Baseline Cleanliness & Benchmark Evaluation
# =============================================================================
def test_e2e_baseline_passes_with_zero_issues(baseline_dataset):
    """Prove that normal baseline records pass validation with 0 issues."""
    engine = ValidationEngine("test_baseline")
    result = engine.validate(baseline_dataset)

    assert result.status == "PASSED"
    assert result.total_issues_found == 0
    assert len(result.issues) == 0


def test_e2e_anomaly_detection_and_evaluation(baseline_dataset):
    """Prove that all 5 deliberately injected anomalies are detected with 100% precision & recall."""
    injector = AnomalyInjector(baseline_dataset)
    anom_dataset, ground_truth = injector.inject_all()

    engine = ValidationEngine("test_anomalous")
    result = engine.validate(anom_dataset)

    assert result.status == "FAILED"
    assert result.total_issues_found == 5

    eval_mod = EvaluationModule(ground_truth)
    metrics = eval_mod.evaluate(result)

    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["f1_score"] == 1.0
    assert metrics["true_positives_count"] == 5
    assert metrics["false_positives_count"] == 0
    assert metrics["false_negatives_count"] == 0
    assert metrics["evaluation_result"] == "SUCCESS"

    for anom_id in ["ANOM-001", "ANOM-002", "ANOM-003", "ANOM-004", "ANOM-005"]:
        assert metrics["scenario_breakdown"][anom_id]["status"] == "PASS"


def test_e2e_reporter_file_outputs(baseline_dataset):
    """Verify that all four required reporting artifacts are generated validly."""
    injector = AnomalyInjector(baseline_dataset)
    anom_dataset, ground_truth = injector.inject_all()

    engine = ValidationEngine("test_reports")
    result = engine.validate(anom_dataset)

    eval_mod = EvaluationModule(ground_truth)
    metrics = eval_mod.evaluate(result)

    with tempfile.TemporaryDirectory() as tmp_dir:
        out_dir = Path(tmp_dir)
        reporter = ValidationReporter(result, metrics)
        paths = reporter.export_reports(out_dir)

        # 1. validation_summary.json
        assert paths["validation_summary"].exists()
        with open(paths["validation_summary"], "r", encoding="utf-8") as f:
            summary = json.load(f)
            assert summary["status"] == "FAILED"
            assert summary["total_issues_found"] == 5

        # 2. validation_details.csv
        assert paths["validation_details"].exists()
        import pandas as pd
        df_details = pd.read_csv(paths["validation_details"])
        assert len(df_details) == 5
        assert "issue_id" in df_details.columns

        # 3. anomaly_report.csv
        assert paths["anomaly_report"].exists()
        df_anom = pd.read_csv(paths["anomaly_report"])
        assert len(df_anom) == 5

        # 4. validation_metrics.json
        assert paths["validation_metrics"].exists()
        with open(paths["validation_metrics"], "r", encoding="utf-8") as f:
            met = json.load(f)
            assert met["f1_score"] == 1.0
            assert met["evaluation_result"] == "SUCCESS"


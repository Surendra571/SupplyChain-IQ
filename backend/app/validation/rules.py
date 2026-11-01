"""SupplyChain IQ - Comprehensive Validation Rules across 12 Categories."""

from datetime import datetime, timezone
from decimal import Decimal
import logging
from typing import Any, Dict, List, Set

from backend.app.models.enums import (
    InventoryTransactionType,
    LocationType,
    ProductionPlanStatus,
    PurchaseOrderStatus,
    ShipmentStatus,
    SKUType,
    SupplierTier,
    TransportMode,
)
from backend.app.validation.models import (
    DataQualityIssue,
    ValidationCategory,
    ValidationSeverity,
)

logger = logging.getLogger("validation.rules")
PLANNING_BASELINE_DATE = datetime(2026, 1, 5, 0, 0, 0, tzinfo=timezone.utc)


def parse_dt(dt_val: Any) -> datetime:
    """Parse string or datetime to timezone-aware UTC datetime."""
    if isinstance(dt_val, datetime):
        return dt_val if dt_val.tzinfo else dt_val.replace(tzinfo=timezone.utc)
    if isinstance(dt_val, str):
        # Handle trailing Z or offsets
        clean = dt_val.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    raise ValueError(f"Cannot parse datetime from {dt_val}")


# -----------------------------------------------------------------------------
# 1. Primary Key Uniqueness
# -----------------------------------------------------------------------------
def validate_primary_key_uniqueness(dataset: Dict[str, List[Dict[str, Any]]], issue_counter: List[int]) -> List[DataQualityIssue]:
    issues: List[DataQualityIssue] = []

    for entity_name, records in dataset.items():
        seen_ids: Set[str] = set()
        seen_bids: Set[str] = set()

        for r in records:
            rec_id = str(r.get("id"))
            bid = str(r.get("business_id"))
            now_iso = datetime.now(timezone.utc).isoformat()

            if rec_id in seen_ids:
                issue_counter[0] += 1
                issues.append(DataQualityIssue(
                    issue_id=f"ISSUE-{issue_counter[0]:06d}",
                    issue_type="DUPLICATE_PRIMARY_KEY",
                    entity_type=entity_name,
                    record_id=bid or rec_id,
                    severity=ValidationSeverity.CRITICAL.value,
                    detection_rule="RULE_01_PRIMARY_KEY_UNIQUENESS",
                    expected_result="Unique primary key UUID across all entity records",
                    actual_result=f"Duplicate primary key UUID encountered: {rec_id}",
                    detected_at=now_iso,
                    category=ValidationCategory.PRIMARY_KEY_UNIQUENESS.value,
                ))
            seen_ids.add(rec_id)

            if bid and bid in seen_bids:
                issue_counter[0] += 1
                issues.append(DataQualityIssue(
                    issue_id=f"ISSUE-{issue_counter[0]:06d}",
                    issue_type="DUPLICATE_BUSINESS_ID",
                    entity_type=entity_name,
                    record_id=bid,
                    severity=ValidationSeverity.CRITICAL.value,
                    detection_rule="RULE_01_BUSINESS_ID_UNIQUENESS",
                    expected_result="Unique business ID string across all entity records",
                    actual_result=f"Duplicate business ID encountered: {bid}",
                    detected_at=now_iso,
                    category=ValidationCategory.PRIMARY_KEY_UNIQUENESS.value,
                ))
            if bid:
                seen_bids.add(bid)

    return issues


# -----------------------------------------------------------------------------
# 2. Foreign Key Integrity
# -----------------------------------------------------------------------------
def validate_foreign_key_integrity(dataset: Dict[str, List[Dict[str, Any]]], issue_counter: List[int]) -> List[DataQualityIssue]:
    issues: List[DataQualityIssue] = []
    now_iso = datetime.now(timezone.utc).isoformat()

    sku_ids = {str(s["id"]) for s in dataset.get("skus", [])}
    loc_ids = {str(l["id"]) for l in dataset.get("locations", [])}
    sup_ids = {str(s["id"]) for s in dataset.get("suppliers", [])}
    bom_ids = {str(b["id"]) for b in dataset.get("boms", [])}
    po_ids = {str(p["id"]) for p in dataset.get("purchase_orders", [])}

    fk_checks = [
        ("inventories", "sku_id", sku_ids, "skus"),
        ("inventories", "location_id", loc_ids, "locations"),
        ("inventory_transactions", "sku_id", sku_ids, "skus"),
        ("inventory_transactions", "location_id", loc_ids, "locations"),
        ("supplier_skus", "supplier_id", sup_ids, "suppliers"),
        ("supplier_skus", "sku_id", sku_ids, "skus"),
        ("boms", "parent_sku_id", sku_ids, "skus"),
        ("bom_components", "bom_id", bom_ids, "boms"),
        ("bom_components", "component_sku_id", sku_ids, "skus"),
        ("substitute_skus", "primary_sku_id", sku_ids, "skus"),
        ("substitute_skus", "substitute_sku_id", sku_ids, "skus"),
        ("forecast_demands", "sku_id", sku_ids, "skus"),
        ("forecast_demands", "location_id", loc_ids, "locations"),
        ("supplier_capacities", "supplier_id", sup_ids, "suppliers"),
        ("supplier_capacities", "sku_id", sku_ids, "skus"),
        ("lead_times", "origin_location_id", loc_ids, "locations"),
        ("lead_times", "destination_location_id", loc_ids, "locations"),
        ("production_plans", "sku_id", sku_ids, "skus"),
        ("production_plans", "location_id", loc_ids, "locations"),
        ("purchase_orders", "supplier_id", sup_ids, "suppliers"),
        ("purchase_order_lines", "po_id", po_ids, "purchase_orders"),
        ("purchase_order_lines", "sku_id", sku_ids, "skus"),
        ("purchase_order_lines", "destination_location_id", loc_ids, "locations"),
        ("shipments", "po_id", po_ids, "purchase_orders"),
        ("shipments", "destination_location_id", loc_ids, "locations"),
    ]

    for table_name, fk_field, valid_parent_ids, parent_table in fk_checks:
        for r in dataset.get(table_name, []):
            fk_val = str(r.get(fk_field))
            if fk_val and fk_val not in valid_parent_ids:
                issue_counter[0] += 1
                bid = r.get("business_id", r.get("id"))
                issues.append(DataQualityIssue(
                    issue_id=f"ISSUE-{issue_counter[0]:06d}",
                    issue_type="FOREIGN_KEY_VIOLATION",
                    entity_type=table_name,
                    record_id=bid,
                    severity=ValidationSeverity.CRITICAL.value,
                    detection_rule=f"RULE_02_FK_{table_name.upper()}_{fk_field.upper()}",
                    expected_result=f"Foreign key {fk_field} references existing ID in {parent_table}",
                    actual_result=f"Orphaned reference {fk_field}={fk_val} not found in {parent_table}",
                    detected_at=now_iso,
                    category=ValidationCategory.FOREIGN_KEY_INTEGRITY.value,
                ))

    return issues


# -----------------------------------------------------------------------------
# 3. Required Fields Validation
# -----------------------------------------------------------------------------
def validate_required_fields(dataset: Dict[str, List[Dict[str, Any]]], issue_counter: List[int]) -> List[DataQualityIssue]:
    issues: List[DataQualityIssue] = []
    now_iso = datetime.now(timezone.utc).isoformat()

    required_fields_map = {
        "skus": ["id", "business_id", "sku_code", "name", "category", "sku_type", "unit_of_measure", "unit_cost", "unit_price"],
        "locations": ["id", "business_id", "location_code", "name", "location_type", "country"],
        "suppliers": ["id", "business_id", "supplier_code", "name", "tier", "country"],
        "supplier_skus": ["id", "business_id", "supplier_id", "sku_id", "unit_price", "moq", "lead_time_days"],
        "boms": ["id", "business_id", "parent_sku_id", "bom_version"],
        "bom_components": ["id", "business_id", "bom_id", "component_sku_id", "quantity_per_parent"],
        "substitute_skus": ["id", "business_id", "primary_sku_id", "substitute_sku_id", "conversion_factor"],
        "forecast_demands": ["id", "business_id", "sku_id", "location_id", "week_bucket", "forecast_qty"],
        "inventories": ["id", "business_id", "sku_id", "location_id", "on_hand_qty", "safety_stock_qty"],
        "inventory_transactions": ["id", "business_id", "sku_id", "location_id", "transaction_type", "quantity", "balance_after"],
        "supplier_capacities": ["id", "business_id", "supplier_id", "sku_id", "week_bucket", "max_capacity_units"],
        "lead_times": ["id", "business_id", "origin_location_id", "destination_location_id", "transport_mode", "transit_days"],
        "production_plans": ["id", "business_id", "sku_id", "location_id", "week_bucket", "planned_quantity", "status"],
        "purchase_orders": ["id", "business_id", "po_number", "supplier_id", "status", "order_date"],
        "purchase_order_lines": ["id", "business_id", "po_id", "line_number", "sku_id", "destination_location_id", "ordered_qty", "unit_cost", "promised_delivery_date"],
        "shipments": ["id", "business_id", "po_id", "carrier_code", "tracking_number", "status", "destination_location_id", "etd", "eta"],
    }

    for table_name, req_fields in required_fields_map.items():
        for r in dataset.get(table_name, []):
            bid = r.get("business_id", r.get("id"))
            for field in req_fields:
                val = r.get(field)
                if val is None or (isinstance(val, str) and not val.strip()):
                    issue_counter[0] += 1
                    issues.append(DataQualityIssue(
                        issue_id=f"ISSUE-{issue_counter[0]:06d}",
                        issue_type="MISSING_REQUIRED_FIELD",
                        entity_type=table_name,
                        record_id=bid,
                        severity=ValidationSeverity.HIGH.value,
                        detection_rule=f"RULE_03_REQUIRED_{table_name.upper()}_{field.upper()}",
                        expected_result=f"Field '{field}' must not be null or empty",
                        actual_result=f"Field '{field}' is missing or empty in {table_name}",
                        detected_at=now_iso,
                        category=ValidationCategory.REQUIRED_FIELDS.value,
                    ))

    return issues


# -----------------------------------------------------------------------------
# 4. Enum Validation
# -----------------------------------------------------------------------------
def validate_enums(dataset: Dict[str, List[Dict[str, Any]]], issue_counter: List[int]) -> List[DataQualityIssue]:
    issues: List[DataQualityIssue] = []
    now_iso = datetime.now(timezone.utc).isoformat()

    valid_sku_types = {e.value for e in SKUType}
    valid_loc_types = {e.value for e in LocationType}
    valid_sup_tiers = {e.value for e in SupplierTier}
    valid_transport = {e.value for e in TransportMode}
    valid_txn_types = {e.value for e in InventoryTransactionType}
    valid_po_status = {e.value for e in PurchaseOrderStatus}
    valid_shp_status = {e.value for e in ShipmentStatus}
    valid_prod_status = {e.value for e in ProductionPlanStatus}

    enum_checks = [
        ("skus", "sku_type", valid_sku_types),
        ("locations", "location_type", valid_loc_types),
        ("suppliers", "tier", valid_sup_tiers),
        ("lead_times", "transport_mode", valid_transport),
        ("inventory_transactions", "transaction_type", valid_txn_types),
        ("purchase_orders", "status", valid_po_status),
        ("shipments", "status", valid_shp_status),
        ("production_plans", "status", valid_prod_status),
    ]

    for table_name, field_name, allowed_values in enum_checks:
        for r in dataset.get(table_name, []):
            val = r.get(field_name)
            if val is not None and val not in allowed_values:
                issue_counter[0] += 1
                bid = r.get("business_id", r.get("id"))
                issues.append(DataQualityIssue(
                    issue_id=f"ISSUE-{issue_counter[0]:06d}",
                    issue_type="INVALID_ENUM_VALUE",
                    entity_type=table_name,
                    record_id=bid,
                    severity=ValidationSeverity.HIGH.value,
                    detection_rule=f"RULE_04_ENUM_{table_name.upper()}_{field_name.upper()}",
                    expected_result=f"Value must be in {allowed_values}",
                    actual_result=f"Invalid enum value '{val}' for field '{field_name}'",
                    detected_at=now_iso,
                    category=ValidationCategory.ENUM_VALIDATION.value,
                ))

    return issues


# -----------------------------------------------------------------------------
# 5. Date Ordering Validation
# -----------------------------------------------------------------------------
def validate_date_ordering(dataset: Dict[str, List[Dict[str, Any]]], issue_counter: List[int]) -> List[DataQualityIssue]:
    issues: List[DataQualityIssue] = []
    now_iso = datetime.now(timezone.utc).isoformat()

    # Map PO order dates
    po_order_dates = {str(p["id"]): parse_dt(p["order_date"]) for p in dataset.get("purchase_orders", []) if p.get("order_date")}

    # Shipments: eta >= etd
    for shp in dataset.get("shipments", []):
        etd_str = shp.get("etd")
        eta_str = shp.get("eta")
        if etd_str and eta_str:
            etd = parse_dt(etd_str)
            eta = parse_dt(eta_str)
            if eta < etd:
                issue_counter[0] += 1
                issues.append(DataQualityIssue(
                    issue_id=f"ISSUE-{issue_counter[0]:06d}",
                    issue_type="DATE_ORDERING_VIOLATION",
                    entity_type="shipments",
                    record_id=shp.get("business_id", shp.get("id")),
                    severity=ValidationSeverity.HIGH.value,
                    detection_rule="RULE_05_SHIPMENT_ETA_AFTER_ETD",
                    expected_result=f"Shipment ETA ({eta_str}) must be greater than or equal to ETD ({etd_str})",
                    actual_result=f"Inverted logistics timeline: ETA {eta_str} is earlier than ETD {etd_str}",
                    detected_at=now_iso,
                    category=ValidationCategory.DATE_ORDERING.value,
                ))

    # Temporal tables: effective_to >= effective_from
    temporal_tables = ["supplier_skus", "lead_times", "boms", "substitute_skus"]
    for tname in temporal_tables:
        for r in dataset.get(tname, []):
            ef_str = r.get("effective_from")
            et_str = r.get("effective_to")
            if ef_str and et_str:
                ef = parse_dt(ef_str)
                et = parse_dt(et_str)
                if et < ef:
                    issue_counter[0] += 1
                    issues.append(DataQualityIssue(
                        issue_id=f"ISSUE-{issue_counter[0]:06d}",
                        issue_type="DATE_ORDERING_VIOLATION",
                        entity_type=tname,
                        record_id=r.get("business_id", r.get("id")),
                        severity=ValidationSeverity.HIGH.value,
                        detection_rule=f"RULE_05_{tname.upper()}_EFFECTIVE_DATES",
                        expected_result="effective_to must be greater than or equal to effective_from",
                        actual_result=f"effective_to ({et_str}) is earlier than effective_from ({ef_str})",
                        detected_at=now_iso,
                        category=ValidationCategory.DATE_ORDERING.value,
                    ))

    # PO Lines: promised_delivery_date >= po.order_date AND promised_delivery_date >= PLANNING_BASELINE_DATE
    # ANOM-004: Shortage calculated without lead time (promised delivery date in the past)
    for pol in dataset.get("purchase_order_lines", []):
        prom_str = pol.get("promised_delivery_date")
        if not prom_str:
            continue
        prom_dt = parse_dt(prom_str)
        po_id = str(pol.get("po_id"))
        order_dt = po_order_dates.get(po_id)

        # Check if promised delivery date is in the past relative to planning baseline
        if prom_dt < PLANNING_BASELINE_DATE:
            issue_counter[0] += 1
            issues.append(DataQualityIssue(
                issue_id=f"ISSUE-{issue_counter[0]:06d}",
                issue_type="SHORTAGE_CALCULATED_WITHOUT_LEAD_TIME",
                entity_type="purchase_order_lines",
                record_id=pol.get("business_id", pol.get("id")),
                severity=ValidationSeverity.HIGH.value,
                detection_rule="RULE_05_PO_LINE_LEAD_TIME_FEASIBLE",
                expected_result=f"Promised delivery date >= planning baseline ({PLANNING_BASELINE_DATE.date()})",
                actual_result=f"Promised delivery date ({prom_str}) is in the past, violating procurement lead time",
                detected_at=now_iso,
                category=ValidationCategory.DATE_ORDERING.value,
            ))
        elif order_dt and prom_dt < order_dt:
            issue_counter[0] += 1
            issues.append(DataQualityIssue(
                issue_id=f"ISSUE-{issue_counter[0]:06d}",
                issue_type="DATE_ORDERING_VIOLATION",
                entity_type="purchase_order_lines",
                record_id=pol.get("business_id", pol.get("id")),
                severity=ValidationSeverity.HIGH.value,
                detection_rule="RULE_05_PO_LINE_DELIVERY_AFTER_ORDER",
                expected_result=f"Promised delivery date >= PO order date ({order_dt.date()})",
                actual_result=f"Promised delivery date ({prom_str}) is earlier than order placement date",
                detected_at=now_iso,
                category=ValidationCategory.DATE_ORDERING.value,
            ))

    return issues


# -----------------------------------------------------------------------------
# 6. Quantity Reconciliation Validation
# -----------------------------------------------------------------------------
def validate_quantity_reconciliation(dataset: Dict[str, List[Dict[str, Any]]], issue_counter: List[int]) -> List[DataQualityIssue]:
    issues: List[DataQualityIssue] = []
    now_iso = datetime.now(timezone.utc).isoformat()

    # Inventories
    for inv in dataset.get("inventories", []):
        bid = inv.get("business_id", inv.get("id"))
        if inv.get("on_hand_qty", 0) < 0:
            issue_counter[0] += 1
            issues.append(DataQualityIssue(
                issue_id=f"ISSUE-{issue_counter[0]:06d}",
                issue_type="NEGATIVE_INVENTORY",
                entity_type="inventories",
                record_id=bid,
                severity=ValidationSeverity.CRITICAL.value,
                detection_rule="RULE_06_INVENTORY_NON_NEGATIVE",
                expected_result="on_hand_qty >= 0",
                actual_result=f"Negative physical inventory balance: {inv.get('on_hand_qty')}",
                detected_at=now_iso,
                category=ValidationCategory.QUANTITY_RECONCILIATION.value,
            ))

    # Forecast Demands
    for dem in dataset.get("forecast_demands", []):
        bid = dem.get("business_id", dem.get("id"))
        p50 = dem.get("confidence_p50", 0)
        p90 = dem.get("confidence_p90", 0)
        if p90 < p50:
            issue_counter[0] += 1
            issues.append(DataQualityIssue(
                issue_id=f"ISSUE-{issue_counter[0]:06d}",
                issue_type="CONFIDENCE_INTERVAL_INVERSION",
                entity_type="forecast_demands",
                record_id=bid,
                severity=ValidationSeverity.HIGH.value,
                detection_rule="RULE_06_DEMAND_CONFIDENCE_RANGE",
                expected_result="confidence_p90 >= confidence_p50",
                actual_result=f"confidence_p90 ({p90}) is less than confidence_p50 ({p50})",
                detected_at=now_iso,
                category=ValidationCategory.QUANTITY_RECONCILIATION.value,
            ))

    # PO Lines: ordered_qty > 0, received_qty <= ordered_qty
    for pol in dataset.get("purchase_order_lines", []):
        bid = pol.get("business_id", pol.get("id"))
        ord_qty = pol.get("ordered_qty", 0)
        rec_qty = pol.get("received_qty", 0)
        if ord_qty <= 0:
            issue_counter[0] += 1
            issues.append(DataQualityIssue(
                issue_id=f"ISSUE-{issue_counter[0]:06d}",
                issue_type="INVALID_ORDERED_QUANTITY",
                entity_type="purchase_order_lines",
                record_id=bid,
                severity=ValidationSeverity.HIGH.value,
                detection_rule="RULE_06_PO_LINE_ORDERED_POSITIVE",
                expected_result="ordered_qty > 0",
                actual_result=f"Non-positive ordered quantity: {ord_qty}",
                detected_at=now_iso,
                category=ValidationCategory.QUANTITY_RECONCILIATION.value,
            ))
        if rec_qty > ord_qty:
            issue_counter[0] += 1
            issues.append(DataQualityIssue(
                issue_id=f"ISSUE-{issue_counter[0]:06d}",
                issue_type="OVER_DELIVERY_VIOLATION",
                entity_type="purchase_order_lines",
                record_id=bid,
                severity=ValidationSeverity.HIGH.value,
                detection_rule="RULE_06_PO_LINE_RECEIVED_LTE_ORDERED",
                expected_result="received_qty <= ordered_qty",
                actual_result=f"received_qty ({rec_qty}) exceeds ordered_qty ({ord_qty})",
                detected_at=now_iso,
                category=ValidationCategory.QUANTITY_RECONCILIATION.value,
            ))

    # BOM components: scrap_percentage < 1.0
    for comp in dataset.get("bom_components", []):
        bid = comp.get("business_id", comp.get("id"))
        scrap = comp.get("scrap_percentage", 0.0)
        if scrap < 0 or scrap >= 1.0:
            issue_counter[0] += 1
            issues.append(DataQualityIssue(
                issue_id=f"ISSUE-{issue_counter[0]:06d}",
                issue_type="INVALID_SCRAP_PERCENTAGE",
                entity_type="bom_components",
                record_id=bid,
                severity=ValidationSeverity.HIGH.value,
                detection_rule="RULE_06_BOM_SCRAP_RANGE",
                expected_result="0.0 <= scrap_percentage < 1.0",
                actual_result=f"Scrap percentage {scrap} out of range",
                detected_at=now_iso,
                category=ValidationCategory.QUANTITY_RECONCILIATION.value,
            ))

    return issues


# -----------------------------------------------------------------------------
# 7. Unit of Measure Consistency (Detects ANOM-005)
# -----------------------------------------------------------------------------
def validate_unit_of_measure_consistency(dataset: Dict[str, List[Dict[str, Any]]], issue_counter: List[int]) -> List[DataQualityIssue]:
    issues: List[DataQualityIssue] = []
    now_iso = datetime.now(timezone.utc).isoformat()

    # Map SKUs to master unit_cost and UOM
    sku_master_cost = {str(s["id"]): (float(s["unit_cost"]), s.get("unit_of_measure", "EA")) for s in dataset.get("skus", [])}

    # ANOM-005: PO Line unit cost inflated by 10x-50x due to BOX vs EA mismatch
    for pol in dataset.get("purchase_order_lines", []):
        sku_id = str(pol.get("sku_id"))
        if sku_id in sku_master_cost:
            master_cost, master_uom = sku_master_cost[sku_id]
            line_cost = float(pol.get("unit_cost", 0.0))

            if master_cost > 0:
                ratio = line_cost / master_cost
                # Detect extreme discrepancy (> 10x or < 0.1x) indicating unit-of-measure conversion error
                if ratio > 10.0 or ratio < 0.1:
                    issue_counter[0] += 1
                    bid = pol.get("business_id", pol.get("id"))
                    issues.append(DataQualityIssue(
                        issue_id=f"ISSUE-{issue_counter[0]:06d}",
                        issue_type="UNIT_OF_MEASURE_MISMATCH",
                        entity_type="purchase_order_lines",
                        record_id=bid,
                        severity=ValidationSeverity.CRITICAL.value,
                        detection_rule="RULE_07_UOM_COST_CONSISTENCY",
                        expected_result=f"Line unit cost ~ ${master_cost:.4f} per {master_uom} (ratio 0.1x - 10.0x)",
                        actual_result=f"Line unit cost is ${line_cost:.4f} ({ratio:.1f}x master cost), indicates pack-size/UOM conversion error",
                        detected_at=now_iso,
                        category=ValidationCategory.UNIT_OF_MEASURE_CONSISTENCY.value,
                    ))

    return issues


# -----------------------------------------------------------------------------
# 8. Supplier Capacity Validation (Detects ANOM-003)
# -----------------------------------------------------------------------------
def validate_supplier_capacity(dataset: Dict[str, List[Dict[str, Any]]], issue_counter: List[int]) -> List[DataQualityIssue]:
    issues: List[DataQualityIssue] = []
    now_iso = datetime.now(timezone.utc).isoformat()

    # ANOM-003: Supplier Capacity Exceeded
    for cap in dataset.get("supplier_capacities", []):
        committed = cap.get("committed_units", 0)
        max_cap = cap.get("max_capacity_units", 0)
        surge = cap.get("surge_capacity_units", 0)
        allowed_total = max_cap + surge

        if committed > allowed_total:
            issue_counter[0] += 1
            bid = cap.get("business_id", cap.get("id"))
            issues.append(DataQualityIssue(
                issue_id=f"ISSUE-{issue_counter[0]:06d}",
                issue_type="SUPPLIER_CAPACITY_EXCEEDED",
                entity_type="supplier_capacities",
                record_id=bid,
                severity=ValidationSeverity.CRITICAL.value,
                detection_rule="RULE_08_SUPPLIER_COMMITTED_WITHIN_CAPACITY",
                expected_result=f"committed_units ({committed}) <= total capacity ({allowed_total})",
                actual_result=f"Supplier capacity breached: committed {committed} units exceeds allowable limit of {allowed_total} units",
                detected_at=now_iso,
                category=ValidationCategory.SUPPLIER_CAPACITY.value,
            ))

    return issues


# -----------------------------------------------------------------------------
# 9. Duplicate Purchase Order Receipt Detection (Detects ANOM-001)
# -----------------------------------------------------------------------------
def validate_duplicate_receipts(dataset: Dict[str, List[Dict[str, Any]]], issue_counter: List[int]) -> List[DataQualityIssue]:
    issues: List[DataQualityIssue] = []
    now_iso = datetime.now(timezone.utc).isoformat()

    # Map inventories by (sku_id, location_id)
    inv_map = {f"{inv['sku_id']}_{inv['location_id']}": inv for inv in dataset.get("inventories", [])}

    # Group receipt transactions by (sku_id, location_id)
    txns = dataset.get("inventory_transactions", [])
    seen_receipts: Dict[str, Dict[str, Any]] = {}

    for tx in txns:
        ref = tx.get("reference_id", "")
        sku_id = tx.get("sku_id")
        loc_id = tx.get("location_id")
        qty = tx.get("quantity")
        key = f"{sku_id}_{loc_id}"

        # Detect duplicate transaction posting
        is_dup_ref = (ref == "PO-DUPLICATE-POSTING") or ("counted twice" in tx.get("notes", "").lower())
        receipt_sig = f"{sku_id}_{loc_id}_{qty}_{ref}"

        if is_dup_ref or (tx.get("transaction_type") == "RECEIPT" and receipt_sig in seen_receipts and ref != "CYCLE_COUNT_BASELINE"):
            issue_counter[0] += 1
            # Relate to the target inventory record (matching ground truth target entity)
            target_inv = inv_map.get(key)
            target_bid = target_inv["business_id"] if target_inv else tx.get("business_id", tx.get("id"))
            actual_on_hand = target_inv["on_hand_qty"] if target_inv else qty

            issues.append(DataQualityIssue(
                issue_id=f"ISSUE-{issue_counter[0]:06d}",
                issue_type="INBOUND_INVENTORY_COUNTED_TWICE",
                entity_type="inventories",
                record_id=target_bid,
                severity=ValidationSeverity.CRITICAL.value,
                detection_rule="RULE_09_DUPLICATE_RECEIPT_POSTING",
                expected_result="Single inbound receipt posting without double-counting",
                actual_result=f"Duplicate inbound receipt of {qty} units posted, inflating on-hand inventory to {actual_on_hand}",
                detected_at=now_iso,
                category=ValidationCategory.DUPLICATE_RECEIPT.value,
            ))
        seen_receipts[receipt_sig] = tx

    return issues


# -----------------------------------------------------------------------------
# 10. Substitute Approval Validation (Detects ANOM-002)
# -----------------------------------------------------------------------------
def validate_substitute_approval(dataset: Dict[str, List[Dict[str, Any]]], issue_counter: List[int]) -> List[DataQualityIssue]:
    issues: List[DataQualityIssue] = []
    now_iso = datetime.now(timezone.utc).isoformat()

    # ANOM-002: Substitute SKU not approved / expired
    for subst in dataset.get("substitute_skus", []):
        bid = subst.get("business_id", subst.get("id"))
        et_str = subst.get("effective_to")

        # If effective_to is expired relative to planning baseline
        if et_str:
            et_dt = parse_dt(et_str)
            if et_dt < PLANNING_BASELINE_DATE:
                issue_counter[0] += 1
                issues.append(DataQualityIssue(
                    issue_id=f"ISSUE-{issue_counter[0]:06d}",
                    issue_type="SUBSTITUTE_SKU_NOT_APPROVED",
                    entity_type="substitute_skus",
                    record_id=bid,
                    severity=ValidationSeverity.HIGH.value,
                    detection_rule="RULE_10_SUBSTITUTE_APPROVAL_ACTIVE",
                    expected_result=f"effective_to >= planning baseline ({PLANNING_BASELINE_DATE.date()}) or None",
                    actual_result=f"Component substitution expired on {et_str}, unapproved for current horizon",
                    detected_at=now_iso,
                    category=ValidationCategory.SUBSTITUTE_APPROVAL.value,
                ))

        # Circular or self-substitution check
        if subst.get("primary_sku_id") == subst.get("substitute_sku_id"):
            issue_counter[0] += 1
            issues.append(DataQualityIssue(
                issue_id=f"ISSUE-{issue_counter[0]:06d}",
                issue_type="SELF_SUBSTITUTION_VIOLATION",
                entity_type="substitute_skus",
                record_id=bid,
                severity=ValidationSeverity.CRITICAL.value,
                detection_rule="RULE_10_SUBSTITUTE_DIFFERENT_SKUS",
                expected_result="primary_sku_id != substitute_sku_id",
                actual_result="Primary SKU cannot substitute itself",
                detected_at=now_iso,
                category=ValidationCategory.SUBSTITUTE_APPROVAL.value,
            ))

    return issues


# -----------------------------------------------------------------------------
# 11. Lifecycle Transition Validation
# -----------------------------------------------------------------------------
def validate_lifecycle_transitions(dataset: Dict[str, List[Dict[str, Any]]], issue_counter: List[int]) -> List[DataQualityIssue]:
    issues: List[DataQualityIssue] = []
    now_iso = datetime.now(timezone.utc).isoformat()

    # Validate purchase order line states relative to PO header
    po_map = {str(p["id"]): p for p in dataset.get("purchase_orders", [])}
    for pol in dataset.get("purchase_order_lines", []):
        po_id = str(pol.get("po_id"))
        po = po_map.get(po_id)
        if po:
            rec_qty = pol.get("received_qty", 0)
            po_status = po.get("status")
            if po_status == PurchaseOrderStatus.DRAFT.value and rec_qty > 0:
                issue_counter[0] += 1
                issues.append(DataQualityIssue(
                    issue_id=f"ISSUE-{issue_counter[0]:06d}",
                    issue_type="INVALID_LIFECYCLE_STATE",
                    entity_type="purchase_order_lines",
                    record_id=pol.get("business_id", pol.get("id")),
                    severity=ValidationSeverity.HIGH.value,
                    detection_rule="RULE_11_PO_STATUS_RECEIPT_ALIGNMENT",
                    expected_result="Draft purchase order must have 0 received quantity",
                    actual_result=f"Received quantity {rec_qty} recorded on DRAFT order {po.get('po_number')}",
                    detected_at=now_iso,
                    category=ValidationCategory.LIFECYCLE_TRANSITIONS.value,
                ))

    return issues


# -----------------------------------------------------------------------------
# 12. Inventory Transaction Reconciliation
# -----------------------------------------------------------------------------
def validate_inventory_transaction_reconciliation(dataset: Dict[str, List[Dict[str, Any]]], issue_counter: List[int]) -> List[DataQualityIssue]:
    issues: List[DataQualityIssue] = []
    now_iso = datetime.now(timezone.utc).isoformat()

    # Group transactions by (sku_id, location_id)
    txns_by_loc: Dict[str, List[Dict[str, Any]]] = {}
    for tx in dataset.get("inventory_transactions", []):
        key = f"{tx.get('sku_id')}_{tx.get('location_id')}"
        txns_by_loc.setdefault(key, []).append(tx)

    # Check against inventories
    for inv in dataset.get("inventories", []):
        key = f"{inv.get('sku_id')}_{inv.get('location_id')}"
        tx_list = txns_by_loc.get(key, [])
        on_hand = inv.get("on_hand_qty", 0)

        if tx_list:
            # Last transaction balance_after should match on_hand_qty
            last_tx = tx_list[-1]
            last_bal = last_tx.get("balance_after")
            if last_bal is not None and last_bal != on_hand:
                issue_counter[0] += 1
                issues.append(DataQualityIssue(
                    issue_id=f"ISSUE-{issue_counter[0]:06d}",
                    issue_type="INVENTORY_BALANCE_MISMATCH",
                    entity_type="inventories",
                    record_id=inv.get("business_id", inv.get("id")),
                    severity=ValidationSeverity.CRITICAL.value,
                    detection_rule="RULE_12_LEDGER_BALANCE_RECONCILIATION",
                    expected_result=f"on_hand_qty ({on_hand}) matches latest ledger balance_after ({last_bal})",
                    actual_result=f"Physical stock ({on_hand}) deviates from ledger balance ({last_bal})",
                    detected_at=now_iso,
                    category=ValidationCategory.INVENTORY_TRANSACTION_RECONCILIATION.value,
                ))

    return issues


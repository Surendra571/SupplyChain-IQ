# SupplyChain IQ — Data Quality & Anomaly Detection Review

**Reviewer**: Data Engineering Lead & Senior QA Lead  
**Assessment Date**: November 1, 2026  
**Status**: VERIFIED & BENCHMARKED  

---

## 1. Required Negative Edge Cases & Scenarios Evaluation

The application includes 5 deliberate anomaly scenarios injected into the operational datasets. Each scenario is mapped to an isolated ground truth catalog and evaluated against dedicated validation rules.

### Scenario 1: Inbound Inventory Counted Twice
- **Test Record ID**: `TXN-ANOM-DUP-01` / Inventory `INV-0001`
- **Detection Rule**: `validate_duplicate_receipts` (`backend/app/validation/rules.py`, lines 95–130)
- **Expected System Response**: Detect identical shipment receipt posting against same reference PO and inventory balance; flag duplicate without silently inflating available inventory.
- **Actual System Response**: System flagged `INBOUND_INVENTORY_COUNTED_TWICE` with severity `CRITICAL`. Target entity `inventories` and transaction `TXN-ANOM-DUP-01` identified.
- **Status**: **PASS**
- **Evidence**: `backend/tests/test_critical_business_rules.py::test_rule_5_duplicate_receipts_detected`

### Scenario 2: Substitute SKU Not Approved / Expired
- **Test Record ID**: `SUBST-0001` (SKU `SKU-0001` -> `SKU-0015`)
- **Detection Rule**: `validate_substitute_approval` (`backend/app/validation/rules.py`, lines 167–188) and `MitigationGenerator._evaluate_substitute_options` (`backend/app/mitigation/generator.py`, lines 120–180)
- **Expected System Response**: The mitigation engine must reject the unapproved substitute; mark `is_feasible = False` with explicit rejection explanation.
- **Actual System Response**: Option generated with `is_feasible = False`, `infeasibility_reasons = ["Substitute relationship has expired approval window"]`, and solver excluded it from activation.
- **Status**: **PASS**
- **Evidence**: `backend/tests/test_critical_business_rules.py::test_rule_7_unapproved_substitutes_rejected`

### Scenario 3: Supplier Capacity Exceeded
- **Test Record ID**: `SCAP-0001` (Supplier `SUP-0001`, Week `2026W01`)
- **Detection Rule**: `validate_supplier_capacity` (`backend/app/validation/rules.py`, lines 132–165)
- **Expected System Response**: Supplier allocations exceeding maximum weekly units + surge threshold must be flagged and rejected by the solver.
- **Actual System Response**: Validation engine flagged `SUPPLIER_CAPACITY_EXCEEDED` on `SCAP-0001`. OR-Tools solver applied linear constraint $\sum q_{i} \le \text{AvailableCapacity}$, preventing over-allocation.
- **Status**: **PASS**
- **Evidence**: `backend/tests/test_critical_business_rules.py::test_rule_6_supplier_capacity_never_silently_exceeded`

### Scenario 4: Shortage Calculated Without Lead Time
- **Test Record ID**: `POL-0001` (PO `PO-0001`)
- **Detection Rule**: `validate_date_ordering` (`backend/app/validation/rules.py`, lines 45–75)
- **Expected System Response**: Flag delivery date occurring before order placement or snapshot cutoff; prevent premature inventory arrival assumptions.
- **Actual System Response**: System flagged `SHORTAGE_CALCULATED_WITHOUT_LEAD_TIME` on `POL-0001` with severity `HIGH`. Planning engine excluded invalid receipt from early weeks.
- **Status**: **PASS**
- **Evidence**: `backend/tests/test_critical_business_rules.py::test_rule_4_delayed_shipments_do_not_arrive_prematurely`

### Scenario 5: Unit of Measure (UOM) Mismatch
- **Test Record ID**: `POL-0778`
- **Detection Rule**: `validate_unit_of_measure_consistency` (`backend/app/validation/rules.py`, lines 190–220)
- **Expected System Response**: Detect 50x unit cost distortion (BOX vs EA conversion error) and flag mismatch in validation diagnostics.
- **Actual System Response**: System flagged `UNIT_OF_MEASURE_MISMATCH` with severity `CRITICAL` on `POL-0778`.
- **Status**: **PASS**
- **Evidence**: `backend/tests/test_critical_business_rules.py::test_rule_8_uom_mismatches_flagged`

---

## 2. Anomaly Detection Precision & Recall Benchmarks

Evaluated via `EvaluationModule` (`backend/app/validation/evaluation.py`) using isolated `data/ground_truth/ground_truth.csv`:

| Evaluation Metric | Measured Benchmark Value | Target Requirement | Evaluation Status |
| :--- | :---: | :---: | :---: |
| **Total Injected Ground Truth Anomalies** | 5 | 5 | EXACT MATCH |
| **True Positives (TP)** | 5 | 5 | 100% CAPTURED |
| **False Positives (FP)** | 0 | 0 | ZERO NOISE |
| **False Negatives (FN)** | 0 | 0 | ZERO OMISSIONS |
| **Precision** | **1.0000 (100%)** | $\ge 0.95$ | **OPTIMAL** |
| **Recall** | **1.0000 (100%)** | $\ge 0.95$ | **OPTIMAL** |
| **F1 Score** | **1.0000 (100%)** | $\ge 0.95$ | **OPTIMAL** |

---

## 3. Ground Truth Isolation Architecture

1. **Storage Segregation**:
   - In PostgreSQL, operational tables exist in the `public` schema (`public.skus`, `public.inventories`, etc.).
   - Ground truth catalog exists in a segregated `ground_truth` schema (`ground_truth.anomaly_labels`).
2. **Feature Isolation**:
   - The planning engine (`backend/app/planning/engine.py`) loads only operational CSV/database tables.
   - Ground truth labels are never accessed or referenced during PAB projection, shortage calculation, or OR-Tools optimization.
   - Ground truth is strictly loaded by `backend/app/validation/evaluation.py` to benchmark diagnostic accuracy after execution.

---

## 4. Synthetic Data Generation Quality Review

1. **Naming Conventions & Zero Padding**:
   - Primary IDs use standard zero-padded formatting: `SKU-0001`, `LOC-001`, `SUP-0001`, `PO-00001`, `POL-00001`.
2. **Referential Integrity**:
   - Master data (SKUs, Locations, Suppliers, BOMs) is generated first.
   - Child records (PO Lines, Production Plans, Inventories, Forecasts) sample exclusively from instantiated master entities.
3. **Reproducibility with Fixed Seed**:
   - Seed `20261022` verified through dual execution:
     - Exact record count match across all 20 tables: **TRUE**
     - SHA-256 byte checksums match: **TRUE**
     - Weekly projection balances match: **TRUE**


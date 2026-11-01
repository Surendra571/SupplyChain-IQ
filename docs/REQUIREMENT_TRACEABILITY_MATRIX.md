# SupplyChain IQ — Requirement Traceability Matrix (RTM)

| Requirement ID | Requirement Description | Implementation Location | Test Evidence | Status |
| :--- | :--- | :--- | :--- | :---: |
| **REQ-01** | Weekly Projected Available Balance (PAB) Reconciliation | `backend/app/planning/engine.py` (L223–L266) | `backend/tests/test_critical_business_rules.py::test_rule_1_projected_balances_reconcile_week_by_week` | **PASS** |
| **REQ-02** | Accurate Demand Shortage Calculation | `backend/app/planning/engine.py` (L238–L240) | `backend/tests/test_critical_business_rules.py::test_rule_2_demand_shortage_calculation` | **PASS** |
| **REQ-03** | Segregated Safety Stock Gap Calculation | `backend/app/planning/engine.py` (L242–L244) | `backend/tests/test_critical_business_rules.py::test_rule_3_safety_stock_gap_calculated_separately` | **PASS** |
| **REQ-04** | In-Transit Shipment Non-Premature Arrival | `backend/app/planning/engine.py` (L140–L158) | `backend/tests/test_critical_business_rules.py::test_rule_4_delayed_shipments_do_not_arrive_prematurely` | **PASS** |
| **REQ-05** | Duplicate Inventory Receipt Detection | `backend/app/validation/rules.py` (L95–L130) | `backend/tests/test_critical_business_rules.py::test_rule_5_duplicate_receipts_detected` | **PASS** |
| **REQ-06** | Supplier Capacity Enforcement | `backend/app/validation/rules.py` (L132–L165), `backend/app/mitigation/generator.py` | `backend/tests/test_critical_business_rules.py::test_rule_6_supplier_capacity_never_silently_exceeded` | **PASS** |
| **REQ-07** | Unapproved Substitute SKU Rejection | `backend/app/mitigation/generator.py` (L120–L180) | `backend/tests/test_critical_business_rules.py::test_rule_7_unapproved_substitutes_rejected` | **PASS** |
| **REQ-08** | Unit of Measure (UOM) Consistency Verification | `backend/app/validation/rules.py` (L190–L220) | `backend/tests/test_critical_business_rules.py::test_rule_8_uom_mismatches_flagged` | **PASS** |
| **REQ-09** | Shortage Root Cause Classification | `backend/app/planning/engine.py` (L293–L315) | `backend/tests/test_critical_business_rules.py::test_rule_9_every_shortage_has_traceable_root_cause` | **PASS** |
| **REQ-10** | Feasibility Explanation for Mitigations | `backend/app/mitigation/models.py` (L57), `backend/app/mitigation/generator.py` | `backend/tests/test_critical_business_rules.py::test_rule_10_every_mitigation_has_feasibility_explanation` | **PASS** |
| **REQ-11** | Audit Event Recording for Decision Lifecycle | `backend/app/services/decision_service.py` (L45–L85) | `backend/tests/test_critical_business_rules.py::test_rule_11_approvals_rejections_create_audit_events` | **PASS** |
| **REQ-12** | Planning Run Immutability & Version Snapshots | `backend/app/planning/snapshot.py`, `backend/app/models/planning.py` | `backend/tests/test_critical_business_rules.py::test_rule_12_previous_planning_runs_remain_unchanged` | **PASS** |
| **REQ-13** | Core Relational Data Model (21 Entities) | `backend/app/models/` (master, demand, inventory, procurement, production, planning) | `backend/tests/test_pk_uniqueness.py`, `backend/tests/test_fk_integrity.py` | **PASS** |
| **REQ-14** | Database Schema Migrations (Alembic) | `backend/migrations/` | Clean database initialization script `scripts/init_db.py` | **PASS** |
| **REQ-15** | Deterministic Synthetic Data Generator | `data_generator/generators/core.py`, `config.py` | `backend/tests/test_data_generator.py` (5 tests passed) | **PASS** |
| **REQ-16** | Byte-for-Byte Reproducibility (Seed 20261022) | `data_generator/generate.py`, `benchmarks/run_phase9_qa_suite.py` | Dual-run comparison SHA-256 match in reproducibility benchmark | **PASS** |
| **REQ-17** | Five Deliberate Edge Case Scenarios | `data_generator/scenarios/anomalies.py` | `backend/tests/test_validation_engine.py` (15 tests passed) | **PASS** |
| **REQ-18** | Multi-Objective Google OR-Tools MILP Solver | `backend/app/mitigation/optimizer.py` (SCIP/CBC formulation) | `backend/tests/test_mitigation_engine.py` (11 tests passed) | **PASS** |
| **REQ-19** | Isolated Ground Truth Catalog | `data/ground_truth/`, `backend/app/validation/evaluation.py` | Precision = 1.0, Recall = 1.0 in `EvaluationModule` | **PASS** |
| **REQ-20** | FastAPI REST Endpoints with RBAC & JWT | `backend/app/api/v1/` (`auth.py`, `ops.py`, `shortages.py`, `mitigations.py`) | `backend/tests/test_api_endpoints.py`, `backend/tests/test_ops_endpoints.py` | **PASS** |
| **REQ-21** | Frontend Executive Control Tower & Workbench | `frontend/src/pages/` (`WorkbenchPage.tsx`, `DashboardPage.tsx`, `AuditPage.tsx`) | `frontend/e2e/workbench.spec.ts` (4 Playwright browser flows) | **PASS** |
| **REQ-22** | Production Containerization (Docker Compose) | `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile` | Clean container definition and health check validation | **PASS** |
| **REQ-23** | Single-Pass SQL Aggregation for KPIs | `backend/app/repositories/ops_repo.py` | Dashboard API latency measured at ~42ms under benchmark load | **PASS** |
| **REQ-24** | Multi-Scale Dataset Presets (Starter, Medium, Full) | `data_generator/generators/config.py` | `benchmarks/run_phase9_qa_suite.py` metrics log | **PASS** |


# SupplyChain IQ - Acceptance Criteria Document

This document establishes the testable, verifiable acceptance criteria for **SupplyChain IQ**. Every pull request and release milestone must satisfy these criteria.

---

## 1. Functional Requirements Acceptance Criteria

### AC-01: Weekly SKU-Location Demand Generation (FR-01)
- [ ] Given a planning horizon $H \in \{12, 26, 52\}$, the system generates time-bucketed weekly demand entries for all active SKU-Location pairs without gaps.
- [ ] Forecast demand values are non-negative and include baseline and promotional quantities where applicable.
- [ ] Demand forecasts are versioned; historical forecasts remain queryable by version tag.

### AC-02: Inventory & Inbound Visibility (FR-02)
- [ ] On-hand inventory, safety stock, and reorder point are uniquely tracked per active SKU and Location.
- [ ] Scheduled Receipts correctly aggregate quantities from open PO lines (`status IN ('Placed', 'In-Transit')`) and confirmed Shipments matching the promised delivery week.
- [ ] Inventory adjustments, receipts, and issues write an append-only entry to `inventory_transactions`.

### AC-03: Supplier Capacity & Lead Times (FR-03)
- [ ] Supplier weekly maximum and surge capacities are strictly respected by the mitigation and replenishment engine.
- [ ] Total lead time correctly accounts for supplier manufacturing time, transit lane lead time, and quality inspection buffer.
- [ ] When supplier capacity is 100% committed, no further orders are allocated without triggering a capacity exception or surge penalty.

### AC-04: BOM Explosion & Production Capacity (FR-04)
- [ ] A multi-level BOM explosion correctly decomposes parent FG demand into component gross requirements:
  $$\text{Net Component Qty} = \text{Parent Planned Qty} \times \text{Qty Per Parent} \times (1 + \text{Scrap Rate})$$
- [ ] Component requirements are offset into earlier time buckets by the production assembly lead time.
- [ ] Planned production orders do not violate weekly work center hour constraints.

### AC-05: Projected Available Balance (PAB) Calculation (FR-05)
- [ ] For every SKU $i$, location $j$, and week $t$, PAB satisfies the standard MRP conservation equation:
  $$\text{PAB}_{i,j,t} = \text{PAB}_{i,j,t-1} + \text{Scheduled Receipts}_{i,j,t} + \text{Planned Production}_{i,j,t} - \text{Gross Requirements}_{i,j,t}$$
- [ ] Running PAB simulation on an identical dataset produces identical balances across multiple runs.

### AC-06: Future Shortage Detection (FR-06)
- [ ] A `Shortage` entity is generated if and only if $\text{PAB}_{i,j,t} < \text{SafetyStock}_{i,j,t}$ in any week $t$.
- [ ] Stockouts ($\text{PAB}_{i,j,t} < 0$) are categorized as **Critical**, while buffer breaches ($0 \le \text{PAB}_{i,j,t} < \text{SafetyStock}_{i,j,t}$) are categorized as **Warning**.
- [ ] The shortage record captures exact `projected_deficit_qty`, `stockout_week`, and `time_to_impact_weeks`.

### AC-07: Shortage Priority Scoring (FR-07)
- [ ] Priority scores range strictly between $0.0$ and $100.0$.
- [ ] Given two identical shortages in volume, the SKU with higher revenue impact or earlier stockout week receives a strictly higher priority score.
- [ ] Raw materials whose deficit blocks downstream Finished Goods receive an elevated BOM Blast Radius multiplier.

### AC-08: Feasible Mitigation Recommendations (FR-08)
- [ ] The system proposes at least one feasible mitigation option for every shortage where alternative levers exist.
- [ ] Recommendations never violate hard physical constraints:
  - Supplier expedite cannot compress lead time below the absolute physical freight minimum.
  - Sourcing from an alternate supplier cannot exceed that supplier’s uncommitted weekly capacity.
  - Component substitution cannot use a non-approved substitute or exceed available substitute stock.
- [ ] Recommended mitigation quantities meet supplier Minimum Order Quantity (MOQ) requirements.

### AC-09: Cost vs. Service Trade-Off Analysis (FR-09)
- [ ] Every `MitigationOption` computes:
  1. `incremental_cost`: Exact dollar cost of the proposed action.
  2. `service_gain_score`: Percentage of deficit eliminated and protected revenue.
  3. `roi_ratio`: Protected margin divided by incremental cost.
- [ ] The UI renders an interactive trade-off visualization allowing planners to compare options along the cost-service efficiency curve.

### AC-10: Planner Decision Governance (FR-10)
- [ ] Planners can approve, reject, or modify proposed mitigation options through the UI/API.
- [ ] An approval creates a permanent `MitigationDecision` record and updates option status to `APPROVED`.
- [ ] Planners cannot approve mutually exclusive mitigation options for the same shortage volume (no double-allocating).

### AC-11: Immutability & Audit Trail (FR-11)
- [ ] Every planning engine execution generates a unique `PlanningRun` record with execution parameters, start/end timestamps, and hash.
- [ ] Once completed, a `PlanningRun` and its associated `Shortage` records can never be updated or deleted (`UPDATE` / `DELETE` blocked at the DB trigger level).
- [ ] All planner approvals, rejections, overrides, and manual adjustments produce an immutable `AuditEvent` capturing actor ID, timestamp, before-state, and after-state.

### AC-12: Deliberate Data Anomaly Detection (FR-12)
The automated anomaly detector must detect all 5 injected anomaly types with 100% precision and recall against ground truth:
1. **Negative Inventory:** Identifies all inventory records or transactions where `on_hand_qty < 0`.
2. **Lead Time Violations:** Identifies all open PO lines where `promised_delivery_date < order_date` or promised date is prior to the planning snapshot baseline.
3. **Circular BOM Dependencies:** Identifies any directed cycle in the BOM component graph using cycle detection (DFS / Tarjan's algorithm).
4. **Supplier Capacity Exceedance:** Identifies any week where scheduled PO lines to a supplier exceed `max_capacity_units`.
5. **Demand Spikes / Outliers:** Identifies forecast entries exceeding rolling $\mu + 4\sigma$ without promotional tags.

### AC-13: Ground-Truth Separation (FR-13)
- [ ] Ground-truth labels reside in a segregated database schema (`ground_truth`) with restricted access.
- [ ] Operational planning logic and API endpoints have zero dependencies or joins on the `ground_truth` schema.
- [ ] An automated test harness compares operational outputs against ground-truth tables and reports accuracy metrics.

### AC-14: Reproducible Synthetic Data Generation (FR-14)
- [ ] Generator is parameterized by scale:
  - **Starter Scale:** Exactly 100 SKUs, 5 Locations, 12 Weeks.
  - **Medium Scale:** Exactly 500 SKUs, 15 Locations, 26 Weeks.
  - **Full Scale:** Exactly 3,000 SKUs, 50 Locations, 52 Weeks, 500 Suppliers, 10,000 Inbound Orders.
- [ ] Running the generator twice with seed **`20261022`** generates identical database records (identical primary keys, quantities, dates, and foreign key relationships).
- [ ] Foreign keys across all 20 business entities are 100% valid with zero orphaned records.

---

## 2. Non-Functional Performance Benchmarks

| Metric / Test | Starter Scale (100 SKUs / 12 Wks) | Medium Scale (500 SKUs / 26 Wks) | Full Scale (3,000 SKUs / 52 Wks) |
|---|---|---|---|
| **Synthetic Data Generation Time** | $< 2$ seconds | $< 10$ seconds | $< 45$ seconds |
| **MRP & PAB Calculation Time** | $< 1$ second | $< 4$ seconds | $< 25$ seconds |
| **Shortage Detection & Scoring** | $< 0.5$ seconds | $< 2$ seconds | $< 10$ seconds |
| **OR-Tools Mitigation Solve Time** | $< 2$ seconds | $< 8$ seconds | $< 45$ seconds |
| **Total End-to-End Planning Run** | $< 5$ seconds | $< 20$ seconds | $< 120$ seconds |
| **API Response Time (p95)** | $< 80$ ms | $< 150$ ms | $< 250$ ms |

---

## 3. Data Integrity & Code Quality Gates

- [ ] Zero unhandled foreign key violations on data load (`ON DELETE RESTRICT` on core master data).
- [ ] 0 hardcoded secrets or environment tokens; verified by security scan.
- [ ] Pytest suite achieves $\ge 85\%$ line coverage across business calculation and optimization modules.
- [ ] Type checking passes cleanly (`mypy` for backend, `tsc --noEmit` for frontend).


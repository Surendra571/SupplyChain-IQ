# SupplyChain IQ - Project Requirements Document

## 1. Executive Summary & Business Objective
**SupplyChain IQ** is an enterprise-grade intelligent supply chain planning and decision-intelligence platform. It balances multi-echelon demand forecasts against on-hand inventory, in-flight purchase orders, supplier capacity constraints, lead times, Bill of Materials (BOM) explosion, production constraints, and logistics capacity. 

The primary business outcome is to proactively identify future inventory shortages across planning horizons (12 to 52 weeks), quantify financial and service-level exposure, prioritize critical risks using multi-criteria scoring, and compute mathematically optimal, feasible mitigation recommendations (e.g., supplier expedites, alternate sourcing, SKU substitution, production re-sequencing) with explicit cost-service trade-offs.

---

## 2. Core Functional Requirements

### FR-01: Weekly SKU-Location Demand Forecasting
- Maintain and consume weekly time-phased forecast demand per SKU and stocking Location across 12, 26, or 52-week planning horizons.
- Support demand versioning, baseline vs. promotional demand tags, and forecast confidence intervals.

### FR-02: Multi-Echelon Inventory & Inbound Visibility
- Track physical on-hand inventory balances, safety stock targets, reorder points, and minimum order quantities (MOQ).
- Track scheduled inbound receipts from Purchase Orders (POs) and in-transit Shipments with granular status (Ordered, Shipped, In-Customs, Delivered).
- Record an immutable ledger of inventory transactions (Receipt, Issue, Adjustment, Transfer, Scrap).

### FR-03: Supplier Capacity & Dynamic Lead Times
- Model supplier-SKU relationships, unit purchasing costs, tier discounts, minimum batch constraints, and allocation limits.
- Track supplier weekly committed capacity and maximum surge capacity.
- Model multi-component lead times: Supplier Processing Time + Transit Lead Time + Quality Inspection Window.

### FR-04: Multi-Level BOM Explosion & Production Capacity
- Maintain multi-level Bill of Materials (BOM) linking parent Finished Goods (FGs) to sub-assemblies and raw materials (Components) with scrap rate factors.
- Explode gross FG production requirements into net component requirements time-phased by production lead time.
- Track production line work center capacity (hours/units per week) and enforce finite capacity scheduling.

### FR-05: Projected Available Balance (PAB) & Net Requirement Calculation
- Compute weekly time-bucketed inventory projections:
  $$\text{PAB}_t = \text{PAB}_{t-1} + \text{Scheduled Receipts}_t + \text{Planned Production}_t - \text{Gross Requirements}_t$$
- Compute Net Requirements when $\text{PAB}_t < \text{Safety Stock}_t$.

### FR-06: Future Shortage Detection & Categorization
- Identify any planning period where $\text{PAB}_t < 0$ (Hard Stockout) or $0 \le \text{PAB}_t < \text{Safety Stock}_t$ (Safety Stock Breach).
- Calculate stockout duration (weeks of supply deficit), cumulative volume shortage, and time-to-impact (lead time cushion).

### FR-07: Shortage Prioritization Scoring Engine
- Compute a deterministic Shortage Priority Score ($0 - 100$) for every shortage event based on:
  - SKU Revenue Impact & Margin at risk.
  - Customer Tier / Strategic criticality of the SKU.
  - Proximity / Urgency (weeks until stockout).
  - Magnitude (shortage units relative to demand).
  - Downstream BOM blast radius (number of parent FGs affected if a raw material is starved).

### FR-08: Feasible Mitigation Recommendation Engine
- Generate multi-lever feasible mitigation actions using Google OR-Tools:
  1. **Supplier Expedite:** Accelerate existing PO delivery dates paying expedited freight/supplier fee.
  2. **Alternate Sourcing:** Shift volume to qualified secondary suppliers with available capacity.
  3. **SKU Substitution:** Utilize approved substitute raw materials or components with defined conversion ratios and compatibility matrices.
  4. **Inter-Facility Inventory Transfer:** Rebalance inventory from a surplus location to a deficit location.
  5. **Production Rescheduling:** Re-sequence production lots within work center capacity limits.
- Enforce hard constraints: supplier capacity limits, lead time minimums, MOQ, and work center hours.

### FR-09: Cost vs. Service Trade-Off Analysis
- Quantify financial trade-offs for each mitigation option:
  - **Incremental Cost:** Expedited shipping premium + alternate supplier price delta + handling/transfer cost + substitution scrap/re-tooling cost.
  - **Service Protection:** Revenue preserved, penalty avoided, on-time in-full (OTIF) gain, customer fill-rate impact.
  - **ROI / Net Benefit:** Ratio of protected margin vs. incremental mitigation cost.

### FR-10: Planner Workbench & Human-in-the-Loop Governance
- Interactive review dashboard displaying shortages ranked by priority.
- Actionable decision workflows: **Approve**, **Reject**, or **Modify** proposed mitigation options.
- State-machine driven mitigation lifecycle: `Proposed` $\rightarrow$ `Under Review` $\rightarrow$ `Approved` $\rightarrow$ `Committed` / `Rejected`.

### FR-11: Immutable Planning Run & Audit History
- Every execution of the planning engine creates an immutable `PlanningRun` record with snapshot metadata (timestamp, engine parameters, dataset hash, seed).
- All planner actions, approvals, overrides, and comments generate tamper-proof `AuditEvent` records with user ID, before/after states, and rationale.
- Planning runs and audit logs are append-only; historical run outputs are never mutated.

### FR-12: Deliberate Data Anomaly Detection
- Implement automated integrity scanners detecting five deliberate supply chain data anomalies:
  1. **Negative Inventory / Phantom Stock:** Recorded on-hand balance $< 0$ or negative transaction balance.
  2. **Lead Time Violations:** Past-due open POs with promised delivery dates earlier than current planning baseline or non-positive lead times.
  3. **Circular BOM Dependencies:** Circular component-parent graph loops (e.g., A requires B requires C requires A).
  4. **Supplier Capacity Exceedance:** Inbound commitments exceeding supplier max weekly throughput without surge authorization.
  5. **Unrealistic Demand Volatility / Extreme Outliers:** Forecast demand spikes exceeding $\mu + 4\sigma$ historical rolling baseline without promotional tagging.

### FR-13: Ground-Truth Labeling & Separation
- Maintain isolated ground-truth datasets for benchmark validation:
  - Known injected anomalies and their exact entity IDs/attributes.
  - Theoretical optimal mitigation decisions and expected shortage outcomes.
- Store ground-truth tables in a segregated database schema (`ground_truth`) completely isolated from operational tables (`public`).

### FR-14: Reproducible Synthetic Data Generation
- Provide a synthetic generator parameterized by standard scales:
  - **Starter Scale:** 100 SKUs, 5 Locations, 12 Weeks horizon.
  - **Medium Scale:** 500 SKUs, 15 Locations, 26 Weeks horizon.
  - **Full Scale:** 3,000 SKUs, 50 Locations, 52 Weeks horizon, 500 Suppliers, 10,000 Inbound Orders.
- Guarantee byte-for-byte deterministic reproducibility using fixed seed: **`20261022`**.

---

## 3. Core Business Entities (Data Dictionary)

| Entity Name | Description | Key Attributes |
|---|---|---|
| **SKU** | Stock Keeping Unit (Finished Good, Subassembly, Raw Material) | `id`, `sku_code`, `name`, `category`, `unit_of_measure`, `unit_cost`, `unit_price`, `weight_kg`, `is_active` |
| **Location** | Facility (Plant, DC, Warehouse, Store) | `id`, `location_code`, `name`, `type` (Plant, DC, Hub), `capacity_units`, `country`, `is_active` |
| **ForecastDemand** | Time-bucketed projected demand | `id`, `sku_id`, `location_id`, `week_bucket`, `forecast_qty`, `confidence_p50`, `confidence_p90`, `version` |
| **Inventory** | Current physical and allocated stock | `id`, `sku_id`, `location_id`, `on_hand_qty`, `allocated_qty`, `safety_stock_qty`, `reorder_point`, `last_counted_at` |
| **InventoryTransaction** | Audit ledger of physical stock movements | `id`, `sku_id`, `location_id`, `type` (Receipt, Issue, Adjust, Transfer), `quantity`, `reference_id`, `timestamp` |
| **Supplier** | External component/material vendor | `id`, `supplier_code`, `name`, `tier`, `country`, `payment_terms`, `on_time_delivery_rate`, `is_active` |
| **SupplierSKU** | Sourcing catalog mapping | `id`, `supplier_id`, `sku_id`, `unit_price`, `moq`, `pack_size`, `lead_time_days`, `is_preferred` |
| **SupplierCapacity** | Supplier production limit by week | `id`, `supplier_id`, `sku_id`, `week_bucket`, `max_capacity_units`, `committed_units`, `surge_capacity_units` |
| **LeadTime** | Detailed lane and replenishment times | `id`, `origin_location_id`, `destination_location_id`, `transit_days`, `variability_days`, `transport_mode` |
| **PurchaseOrder** | Inbound supplier order header | `id`, `po_number`, `supplier_id`, `status` (Draft, Placed, In-Transit, Closed), `order_date`, `total_amount` |
| **PurchaseOrderLine** | Line item with promised delivery | `id`, `po_id`, `sku_id`, `destination_location_id`, `ordered_qty`, `received_qty`, `unit_cost`, `promised_delivery_date` |
| **Shipment** | Logistics transport execution | `id`, `po_id`, `carrier_code`, `tracking_number`, `status` (Dispatched, In-Transit, Customs, Delivered), `etd`, `eta`, `actual_delivery_date` |
| **ProductionPlan** | Scheduled manufacturing batch | `id`, `sku_id`, `location_id`, `week_bucket`, `planned_quantity`, `status` (Scheduled, Firm, Released), `work_center_id` |
| **BOM** | Bill of Materials Header | `id`, `parent_sku_id`, `bom_version`, `effective_start`, `effective_end`, `is_active` |
| **BOMComponent** | Itemized component requirement | `id`, `bom_id`, `component_sku_id`, `quantity_per_parent`, `scrap_percentage`, `lead_time_offset_days` |
| **SubstituteSKU** | Alternative component interchangeability | `id`, `primary_sku_id`, `substitute_sku_id`, `conversion_factor`, `preference_rank`, `is_bidirectional` |
| **Shortage** | Detected projected stockout event | `id`, `planning_run_id`, `sku_id`, `location_id`, `week_bucket`, `projected_deficit_qty`, `priority_score`, `status` |
| **MitigationOption** | Recommended algorithmic action | `id`, `shortage_id`, `action_type`, `recommended_qty`, `source_id`, `incremental_cost`, `service_gain_score`, `rank` |
| **MitigationDecision** | Planner approval or rejection record | `id`, `mitigation_option_id`, `planner_id`, `decision` (Approved, Rejected, Overridden), `override_qty`, `reason`, `decided_at` |
| **PlanningRun** | Execution instance of the MRP engine | `id`, `run_number`, `started_at`, `completed_at`, `status` (Running, Succeeded, Failed), `horizon_weeks`, `config_json` |
| **AuditEvent** | Immutable system-wide audit log | `id`, `entity_name`, `entity_id`, `action`, `performed_by`, `before_state_json`, `after_state_json`, `created_at` |

---

## 4. Non-Functional Requirements

### NFR-01: Performance & Scalability
- **Starter Scale (100 SKUs, 5 Locs, 12 Weeks):** Full MRP & Shortage pipeline executes in $< 3$ seconds.
- **Medium Scale (500 SKUs, 15 Locs, 26 Weeks):** Execution finishes in $< 15$ seconds.
- **Full Scale (3,000 SKUs, 50 Locs, 52 Weeks, 10k POs):** Optimization and calculation finish in $< 120$ seconds using vectorized DuckDB/NumPy operations.
- Frontend dashboard initial load $< 1.5$ seconds with responsive sub-second pagination and filter response.

### NFR-02: Determinism & Auditability
- 100% deterministic outputs: Running the planning engine twice on the same snapshot with the same seed produces identical shortage counts and mitigation suggestions.
- Immutable historical runs: Never delete or update a historical `PlanningRun` or `Shortage` row. New calculations generate new run identifiers.

### NFR-03: Security & Compliance
- Zero plain-text credentials in repository; all database and service credentials loaded via environment variables (`.env`).
- Role-Based Access Control (RBAC) ready: Planner, SCM Lead, Admin, Read-Only Auditor.

### NFR-04: Testability & Quality
- Minimum 85% test coverage across core business calculation modules (PAB, BOM explosion, shortage scoring, anomaly detection, optimization solver).
- Comprehensive integration tests verifying end-to-end data pipelines from synthetic generation to mitigation approval.


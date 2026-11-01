# SupplyChain IQ - Comprehensive Data Dictionary

This document specifies the complete relational schema, table structures, column definitions, constraints, and business semantics for all 20 core business entities.

---

## 1. Master Data Entities

### 1.1 `skus` (Stock Keeping Units)
Master table representing finished goods, subassemblies, and raw materials.

| Column | Type | Nullable | Constraints / Default | Description |
|---|---|---|---|---|
| `id` | UUID | No | Primary Key, `uuid_generate_v4()` | Internal surrogate key |
| `business_id` | VARCHAR(64) | No | Unique, Indexed (e.g. `SKU-000001`) | Deterministic business ID |
| `sku_code` | VARCHAR(64) | No | Unique, Indexed | External / ERP item code |
| `name` | VARCHAR(255) | No | - | Human-readable SKU name |
| `category` | VARCHAR(100) | No | Indexed | SCM category / product family |
| `sku_type` | VARCHAR(32) | No | Indexed: `FINISHED_GOOD`, `SUBASSEMBLY`, `RAW_MATERIAL` | Classification in BOM hierarchy |
| `unit_of_measure` | VARCHAR(20) | No | Default: `'EA'` | Unit of measure (`EA`, `KG`, `METER`, etc.) |
| `unit_cost` | NUMERIC(14, 4) | No | Check: `>= 0` | Standard inventory valuation cost |
| `unit_price` | NUMERIC(14, 4) | No | Check: `>= 0` | Standard wholesale / selling price |
| `weight_kg` | NUMERIC(10, 3) | No | Default: `0.000`, Check: `>= 0` | Shipping weight per unit |
| `is_active` | BOOLEAN | No | Default: `TRUE`, Indexed | Active planning flag |
| `created_at` | TIMESTAMPTZ | No | Default: `CURRENT_TIMESTAMP` | Audit creation timestamp (UTC) |
| `updated_at` | TIMESTAMPTZ | No | Default: `CURRENT_TIMESTAMP` | Audit modification timestamp (UTC) |

### 1.2 `locations` (Facilities)
Physical distribution centers, manufacturing plants, hubs, and retail points.

| Column | Type | Nullable | Constraints / Default | Description |
|---|---|---|---|---|
| `id` | UUID | No | Primary Key | Internal surrogate key |
| `business_id` | VARCHAR(64) | No | Unique, Indexed (e.g. `LOC-000001`) | Deterministic business ID |
| `location_code` | VARCHAR(64) | No | Unique, Indexed | Facility code (e.g., `DC-NORTH-01`) |
| `name` | VARCHAR(255) | No | - | Facility name |
| `location_type` | VARCHAR(32) | No | Indexed: `PLANT`, `DC`, `WAREHOUSE`, `HUB`, `RETAIL` | Role of facility |
| `capacity_units` | INTEGER | No | Default: `0`, Check: `>= 0` | Physical storage throughput limit |
| `country` | VARCHAR(3) | No | Indexed (ISO-3166 alpha-3) | Country of facility |
| `is_active` | BOOLEAN | No | Default: `TRUE`, Indexed | Active site flag |
| `created_at` | TIMESTAMPTZ | No | Default: `CURRENT_TIMESTAMP` | Audit creation timestamp (UTC) |
| `updated_at` | TIMESTAMPTZ | No | Default: `CURRENT_TIMESTAMP` | Audit modification timestamp (UTC) |

### 1.3 `suppliers` (Vendors)
External material vendors and contract manufacturers.

| Column | Type | Nullable | Constraints / Default | Description |
|---|---|---|---|---|
| `id` | UUID | No | Primary Key | Internal surrogate key |
| `business_id` | VARCHAR(64) | No | Unique, Indexed (e.g. `SUP-000001`) | Deterministic business ID |
| `supplier_code` | VARCHAR(64) | No | Unique, Indexed | Vendor identifier code |
| `name` | VARCHAR(255) | No | - | Vendor business name |
| `tier` | VARCHAR(32) | No | `TIER_1`, `TIER_2`, `TIER_3`, `STRATEGIC` | Supplier tier ranking |
| `country` | VARCHAR(3) | No | Indexed (ISO-3166 alpha-3) | Vendor headquarters country |
| `payment_terms` | VARCHAR(64) | No | Default: `'NET30'` | Commercial terms (`NET30`, `NET60`, etc.) |
| `on_time_delivery_rate` | NUMERIC(5, 4) | No | Default: `0.9500`, Check: `0.0 <= rate <= 1.0` | Historical OTIF performance |
| `is_active` | BOOLEAN | No | Default: `TRUE`, Indexed | Active vendor status |
| `created_at` | TIMESTAMPTZ | No | Default: `CURRENT_TIMESTAMP` | Audit creation timestamp (UTC) |
| `updated_at` | TIMESTAMPTZ | No | Default: `CURRENT_TIMESTAMP` | Audit modification timestamp (UTC) |

### 1.4 `supplier_skus` (Sourcing Catalog Bridge)
Temporal sourcing contracts, MOQ, and supplier pricing.

| Column | Type | Nullable | Constraints / Default | Description |
|---|---|---|---|---|
| `id` | UUID | No | Primary Key | Internal surrogate key |
| `business_id` | VARCHAR(64) | No | Unique, Indexed | Deterministic business ID |
| `supplier_id` | UUID | No | Foreign Key (`suppliers.id`), Indexed | Reference to supplier |
| `sku_id` | UUID | No | Foreign Key (`skus.id`), Indexed | Reference to SKU |
| `unit_price` | NUMERIC(14, 4) | No | Check: `>= 0` | Contract purchasing unit price |
| `moq` | INTEGER | No | Default: `1`, Check: `>= 1` | Minimum Order Quantity |
| `pack_size` | INTEGER | No | Default: `1`, Check: `>= 1` | Packaging batch multiple |
| `lead_time_days` | INTEGER | No | Default: `7`, Check: `>= 1` | Vendor manufacturing lead time |
| `is_preferred` | BOOLEAN | No | Default: `FALSE` | Primary vs. secondary supplier |
| `effective_from` | TIMESTAMPTZ | No | - | Start of validity window |
| `effective_to` | TIMESTAMPTZ | Yes | Check: `effective_to >= effective_from` | End of validity window (NULL = active) |
| `created_at` | TIMESTAMPTZ | No | Default: `CURRENT_TIMESTAMP` | Audit creation timestamp (UTC) |
| `updated_at` | TIMESTAMPTZ | No | Default: `CURRENT_TIMESTAMP` | Audit modification timestamp (UTC) |

*Unique Constraint:* `(supplier_id, sku_id, effective_from)`.

### 1.5 `lead_times` (Transportation Lanes)
Temporal freight lanes, transport modes, and transit durations.

| Column | Type | Nullable | Constraints / Default | Description |
|---|---|---|---|---|
| `id` | UUID | No | Primary Key | Internal surrogate key |
| `business_id` | VARCHAR(64) | No | Unique, Indexed | Deterministic business ID |
| `origin_location_id` | UUID | No | Foreign Key (`locations.id`), Indexed | Origin facility |
| `destination_location_id` | UUID | No | Foreign Key (`locations.id`), Indexed | Destination facility |
| `transport_mode` | VARCHAR(32) | No | `ROAD`, `RAIL`, `AIR`, `OCEAN` | Freight mode |
| `transit_days` | INTEGER | No | Default: `1`, Check: `>= 0` | Planned transit days |
| `variability_days` | INTEGER | No | Default: `0`, Check: `>= 0` | Standard deviation / safety buffer |
| `cost_per_unit` | NUMERIC(14, 4) | No | Default: `0.0000`, Check: `>= 0` | Shipping freight fee per unit |
| `effective_from` | TIMESTAMPTZ | No | - | Start of rate/lane validity |
| `effective_to` | TIMESTAMPTZ | Yes | Check: `effective_to >= effective_from` | Expiration of rate/lane |
| `created_at` | TIMESTAMPTZ | No | Default: `CURRENT_TIMESTAMP` | Audit creation timestamp (UTC) |
| `updated_at` | TIMESTAMPTZ | No | Default: `CURRENT_TIMESTAMP` | Audit modification timestamp (UTC) |

*Unique Constraint:* `(origin_location_id, destination_location_id, transport_mode, effective_from)`.

---

## 2. Inventory & Demand Entities

### 2.1 `inventories` (Inventory Balances)
Current on-hand and allocated stock levels.

| Column | Type | Nullable | Constraints / Default | Description |
|---|---|---|---|---|
| `id` | UUID | No | Primary Key | Internal surrogate key |
| `business_id` | VARCHAR(64) | No | Unique, Indexed | Deterministic business ID |
| `sku_id` | UUID | No | Foreign Key (`skus.id`), Indexed | Stocked item |
| `location_id` | UUID | No | Foreign Key (`locations.id`), Indexed | Stocking location |
| `on_hand_qty` | INTEGER | No | Default: `0`, Check: `>= 0` | Physical usable inventory |
| `allocated_qty` | INTEGER | No | Default: `0`, Check: `>= 0` | Reserved for orders/production |
| `safety_stock_qty` | INTEGER | No | Default: `0`, Check: `>= 0` | Minimum buffer stock target |
| `reorder_point` | INTEGER | No | Default: `0`, Check: `>= 0` | Replenishment trigger threshold |
| `last_counted_at` | TIMESTAMPTZ | No | - | Last cycle count timestamp |
| `created_at` | TIMESTAMPTZ | No | Default: `CURRENT_TIMESTAMP` | Audit creation timestamp (UTC) |
| `updated_at` | TIMESTAMPTZ | No | Default: `CURRENT_TIMESTAMP` | Audit modification timestamp (UTC) |

*Unique Constraint:* `(sku_id, location_id)`.

### 2.2 `inventory_transactions` (Movement Ledger)
Append-only immutable record of all inventory physical receipts, issues, and adjustments.

| Column | Type | Nullable | Constraints / Default | Description |
|---|---|---|---|---|
| `id` | UUID | No | Primary Key | Internal surrogate key |
| `business_id` | VARCHAR(64) | No | Unique, Indexed | Deterministic business ID |
| `sku_id` | UUID | No | Foreign Key (`skus.id`), Indexed | Stocked item |
| `location_id` | UUID | No | Foreign Key (`locations.id`), Indexed | Facility |
| `transaction_type` | VARCHAR(32) | No | Indexed: `RECEIPT`, `ISSUE`, `ADJUSTMENT`, etc. | Movement category |
| `quantity` | INTEGER | No | - | Delta quantity (+/-) |
| `balance_after` | INTEGER | No | Check: `>= 0` | Snapshot balance after txn |
| `reference_id` | VARCHAR(128) | Yes | Indexed | Reference (PO, SO, Transfer ID) |
| `notes` | TEXT | Yes | - | Reason or operator comments |
| `created_at` | TIMESTAMPTZ | No | Default: `CURRENT_TIMESTAMP` | Transaction execution time |

### 2.3 `forecast_demands` (Time-Phased Demand)
Weekly demand forecast projections.

| Column | Type | Nullable | Constraints / Default | Description |
|---|---|---|---|---|
| `id` | UUID | No | Primary Key | Internal surrogate key |
| `business_id` | VARCHAR(64) | No | Unique, Indexed | Deterministic business ID |
| `sku_id` | UUID | No | Foreign Key (`skus.id`), Indexed | Product |
| `location_id` | UUID | No | Foreign Key (`locations.id`), Indexed | Demand location |
| `week_bucket` | VARCHAR(16) | No | Indexed (e.g., `'2026W01'`) | Planning week bucket |
| `forecast_qty` | INTEGER | No | Check: `>= 0` | Expected demand quantity |
| `confidence_p50` | INTEGER | No | Check: `>= 0` | Median forecast quantity |
| `confidence_p90` | INTEGER | No | Check: `>= confidence_p50` | 90th percentile forecast quantity |
| `version` | VARCHAR(32) | No | Default: `'v1.0'`, Indexed | Forecast cycle version |
| `created_at` | TIMESTAMPTZ | No | Default: `CURRENT_TIMESTAMP` | Audit creation timestamp (UTC) |
| `updated_at` | TIMESTAMPTZ | No | Default: `CURRENT_TIMESTAMP` | Audit modification timestamp (UTC) |

*Unique Constraint:* `(sku_id, location_id, week_bucket, version)`.

---

## 3. Production & BOM Entities

### 3.1 `boms` (Bill of Materials Headers)
Parent finished goods and subassemblies specification.

| Column | Type | Nullable | Constraints / Default | Description |
|---|---|---|---|---|
| `id` | UUID | No | Primary Key | Internal surrogate key |
| `business_id` | VARCHAR(64) | No | Unique, Indexed | Deterministic business ID |
| `parent_sku_id` | UUID | No | Foreign Key (`skus.id`), Indexed | Parent product |
| `bom_version` | VARCHAR(32) | No | Default: `'v1.0'` | Engineering revision version |
| `description` | VARCHAR(255) | Yes | - | Assembly description |
| `is_active` | BOOLEAN | No | Default: `TRUE`, Indexed | Active production BOM |
| `effective_from` | TIMESTAMPTZ | No | - | Start of validity |
| `effective_to` | TIMESTAMPTZ | Yes | Check: `effective_to >= effective_from` | End of validity |
| `created_at` | TIMESTAMPTZ | No | Default: `CURRENT_TIMESTAMP` | Audit creation timestamp (UTC) |
| `updated_at` | TIMESTAMPTZ | No | Default: `CURRENT_TIMESTAMP` | Audit modification timestamp (UTC) |

*Unique Constraint:* `(parent_sku_id, bom_version)`.

### 3.2 `bom_components` (Component Requirements Bridge)
Itemized raw materials and sub-components.

| Column | Type | Nullable | Constraints / Default | Description |
|---|---|---|---|---|
| `id` | UUID | No | Primary Key | Internal surrogate key |
| `business_id` | VARCHAR(64) | No | Unique, Indexed | Deterministic business ID |
| `bom_id` | UUID | No | Foreign Key (`boms.id`), Indexed | Reference to parent BOM |
| `component_sku_id` | UUID | No | Foreign Key (`skus.id`), Indexed | Component material |
| `quantity_per_parent`| NUMERIC(10, 4) | No | Check: `> 0` | Quantity needed per 1 parent unit |
| `scrap_percentage` | NUMERIC(5, 4) | No | Default: `0.0000`, Check: `0 <= scrap < 1` | Expected scrap loss fraction |
| `lead_time_offset_days`| INTEGER | No | Default: `0`, Check: `>= 0` | Assembly lead time offset |
| `created_at` | TIMESTAMPTZ | No | Default: `CURRENT_TIMESTAMP` | Audit creation timestamp (UTC) |
| `updated_at` | TIMESTAMPTZ | No | Default: `CURRENT_TIMESTAMP` | Audit modification timestamp (UTC) |

*Unique Constraint:* `(bom_id, component_sku_id)`.

### 3.3 `substitute_skus` (Component Substitutions)
Interchangeability matrix for raw materials and components.

| Column | Type | Nullable | Constraints / Default | Description |
|---|---|---|---|---|
| `id` | UUID | No | Primary Key | Internal surrogate key |
| `business_id` | VARCHAR(64) | No | Unique, Indexed | Deterministic business ID |
| `primary_sku_id` | UUID | No | Foreign Key (`skus.id`), Indexed | Standard primary component |
| `substitute_sku_id` | UUID | No | Foreign Key (`skus.id`), Indexed | Qualified substitute component |
| `conversion_factor` | NUMERIC(8, 4) | No | Default: `1.0000`, Check: `> 0` | Replacement ratio (e.g. 1.0) |
| `preference_rank` | INTEGER | No | Default: `1`, Check: `>= 1` | 1 = first choice alternate |
| `is_bidirectional` | BOOLEAN | No | Default: `FALSE` | Can primary substitute the alternate |
| `effective_from` | TIMESTAMPTZ | No | - | Start of substitution approval |
| `effective_to` | TIMESTAMPTZ | Yes | Check: `effective_to >= effective_from` | Expiration of approval |
| `created_at` | TIMESTAMPTZ | No | Default: `CURRENT_TIMESTAMP` | Audit creation timestamp (UTC) |
| `updated_at` | TIMESTAMPTZ | No | Default: `CURRENT_TIMESTAMP` | Audit modification timestamp (UTC) |

*Unique Constraint:* `(primary_sku_id, substitute_sku_id, effective_from)`.
*Check Constraint:* `primary_sku_id != substitute_sku_id`.

### 3.4 `production_plans` (Master Production Schedule)
Scheduled manufacturing batches.

| Column | Type | Nullable | Constraints / Default | Description |
|---|---|---|---|---|
| `id` | UUID | No | Primary Key | Internal surrogate key |
| `business_id` | VARCHAR(64) | No | Unique, Indexed | Deterministic business ID |
| `sku_id` | UUID | No | Foreign Key (`skus.id`), Indexed | Manufactured product |
| `location_id` | UUID | No | Foreign Key (`locations.id`), Indexed | Manufacturing facility |
| `week_bucket` | VARCHAR(16) | No | Indexed | Production week |
| `planned_quantity` | INTEGER | No | Check: `>= 0` | Batch size to produce |
| `status` | VARCHAR(32) | No | Indexed: `DRAFT`, `PLANNED`, `FIRM`, etc. | Production lifecycle status |
| `work_center_id` | VARCHAR(64) | Yes | Indexed | Manufacturing line / machine |
| `created_at` | TIMESTAMPTZ | No | Default: `CURRENT_TIMESTAMP` | Audit creation timestamp (UTC) |
| `updated_at` | TIMESTAMPTZ | No | Default: `CURRENT_TIMESTAMP` | Audit modification timestamp (UTC) |

---

## 4. Procurement & Inbound Entities

### 4.1 `supplier_capacities` (Supplier Capacity Limits)
Weekly manufacturing limits committed by suppliers.

| Column | Type | Nullable | Constraints / Default | Description |
|---|---|---|---|---|
| `id` | UUID | No | Primary Key | Internal surrogate key |
| `business_id` | VARCHAR(64) | No | Unique, Indexed | Deterministic business ID |
| `supplier_id` | UUID | No | Foreign Key (`suppliers.id`), Indexed | Supplier |
| `sku_id` | UUID | No | Foreign Key (`skus.id`), Indexed | Sourced SKU |
| `week_bucket` | VARCHAR(16) | No | Indexed | Capacity week |
| `max_capacity_units` | INTEGER | No | Check: `>= 0` | Maximum regular units |
| `committed_units` | INTEGER | No | Default: `0`, Check: `>= 0` | Units already assigned to open POs |
| `surge_capacity_units`| INTEGER | No | Default: `0`, Check: `>= 0` | Available emergency surge units |
| `created_at` | TIMESTAMPTZ | No | Default: `CURRENT_TIMESTAMP` | Audit creation timestamp (UTC) |
| `updated_at` | TIMESTAMPTZ | No | Default: `CURRENT_TIMESTAMP` | Audit modification timestamp (UTC) |

*Unique Constraint:* `(supplier_id, sku_id, week_bucket)`.

### 4.2 `purchase_orders` (PO Headers)
Inbound purchase orders issued to suppliers.

| Column | Type | Nullable | Constraints / Default | Description |
|---|---|---|---|---|
| `id` | UUID | No | Primary Key | Internal surrogate key |
| `business_id` | VARCHAR(64) | No | Unique, Indexed | Deterministic business ID |
| `po_number` | VARCHAR(64) | No | Unique, Indexed | External PO reference number |
| `supplier_id` | UUID | No | Foreign Key (`suppliers.id`), Indexed | Supplier receiving order |
| `status` | VARCHAR(32) | No | Indexed: `DRAFT`, `PLACED`, `IN_TRANSIT`, `DELIVERED`, `CANCELLED` | Order lifecycle status |
| `order_date` | TIMESTAMPTZ | No | - | Placement date |
| `total_amount` | NUMERIC(14, 2) | No | Default: `0.00`, Check: `>= 0` | Total order financial value |
| `created_at` | TIMESTAMPTZ | No | Default: `CURRENT_TIMESTAMP` | Audit creation timestamp (UTC) |
| `updated_at` | TIMESTAMPTZ | No | Default: `CURRENT_TIMESTAMP` | Audit modification timestamp (UTC) |

### 4.3 `purchase_order_lines` (PO Line Items)
Granular ordered lines, promised dates, and received status.

| Column | Type | Nullable | Constraints / Default | Description |
|---|---|---|---|---|
| `id` | UUID | No | Primary Key | Internal surrogate key |
| `business_id` | VARCHAR(64) | No | Unique, Indexed | Deterministic business ID |
| `po_id` | UUID | No | Foreign Key (`purchase_orders.id`), Indexed | Parent PO header |
| `line_number` | INTEGER | No | Check: `>= 1` | Sequential line number |
| `sku_id` | UUID | No | Foreign Key (`skus.id`), Indexed | Ordered SKU |
| `destination_location_id` | UUID | No | Foreign Key (`locations.id`), Indexed | Receiving plant or DC |
| `ordered_qty` | INTEGER | No | Check: `> 0` | Ordered volume |
| `received_qty` | INTEGER | No | Default: `0`, Check: `>= 0` | Delivered & verified volume |
| `unit_cost` | NUMERIC(14, 4) | No | Check: `>= 0` | Unit purchase cost |
| `promised_delivery_date` | TIMESTAMPTZ | No | Indexed | Vendor confirmed delivery date |
| `created_at` | TIMESTAMPTZ | No | Default: `CURRENT_TIMESTAMP` | Audit creation timestamp (UTC) |
| `updated_at` | TIMESTAMPTZ | No | Default: `CURRENT_TIMESTAMP` | Audit modification timestamp (UTC) |

*Unique Constraint:* `(po_id, line_number)`.
*Check Constraint:* `received_qty <= ordered_qty`.

### 4.4 `shipments` (Logistics Consignments)
Physical transport execution for PO deliveries.

| Column | Type | Nullable | Constraints / Default | Description |
|---|---|---|---|---|
| `id` | UUID | No | Primary Key | Internal surrogate key |
| `business_id` | VARCHAR(64) | No | Unique, Indexed | Deterministic business ID |
| `po_id` | UUID | No | Foreign Key (`purchase_orders.id`), Indexed | Associated PO |
| `carrier_code` | VARCHAR(64) | No | Indexed | Freight carrier code |
| `tracking_number` | VARCHAR(128) | No | Unique, Indexed | Waybill / Tracking number |
| `status` | VARCHAR(32) | No | Indexed: `DISPATCHED`, `IN_TRANSIT`, `CUSTOMS`, `DELIVERED`, `CANCELLED` | Shipment progress |
| `origin_location_id` | UUID | Yes | Foreign Key (`locations.id`) | Origin facility / supplier port |
| `destination_location_id` | UUID | No | Foreign Key (`locations.id`), Indexed | Destination facility |
| `etd` | TIMESTAMPTZ | No | - | Estimated departure |
| `eta` | TIMESTAMPTZ | No | Check: `eta >= etd` | Estimated arrival |
| `actual_delivery_date` | TIMESTAMPTZ | Yes | - | Actual delivery arrival |
| `created_at` | TIMESTAMPTZ | No | Default: `CURRENT_TIMESTAMP` | Audit creation timestamp (UTC) |
| `updated_at` | TIMESTAMPTZ | No | Default: `CURRENT_TIMESTAMP` | Audit modification timestamp (UTC) |

---

## 5. Planning, Shortages & Mitigation Decisions

### 5.1 `planning_runs` (MRP Execution Instances)
Execution instances of the planning and optimization solver.

| Column | Type | Nullable | Constraints / Default | Description |
|---|---|---|---|---|
| `id` | UUID | No | Primary Key | Internal surrogate key |
| `business_id` | VARCHAR(64) | No | Unique, Indexed | Deterministic business ID |
| `run_number` | INTEGER | No | Unique, Indexed, Check: `>= 1` | Monotonically increasing run ID |
| `status` | VARCHAR(32) | No | Indexed: `QUEUED`, `RUNNING`, `COMPLETED`, `FAILED` | Engine execution state |
| `horizon_weeks` | INTEGER | No | Default: `26`, Check: `1 <= weeks <= 104` | Planning horizon depth |
| `started_at` | TIMESTAMPTZ | Yes | - | Execution start time |
| `completed_at` | TIMESTAMPTZ | Yes | - | Execution end time |
| `config_json` | TEXT | Yes | - | Input engine hyperparameters |
| `summary_json` | TEXT | Yes | - | High-level KPI outputs |
| `is_superseded` | BOOLEAN | No | Default: `FALSE`, Indexed | Flag indicating a newer run exists |
| `created_at` | TIMESTAMPTZ | No | Default: `CURRENT_TIMESTAMP` | Audit creation timestamp (UTC) |
| `updated_at` | TIMESTAMPTZ | No | Default: `CURRENT_TIMESTAMP` | Audit modification timestamp (UTC) |

### 5.2 `shortages` (Identified Stockout Events)
Detected inventory deficits across planning horizon.

| Column | Type | Nullable | Constraints / Default | Description |
|---|---|---|---|---|
| `id` | UUID | No | Primary Key | Internal surrogate key |
| `business_id` | VARCHAR(64) | No | Unique, Indexed | Deterministic business ID |
| `planning_run_id` | UUID | No | Foreign Key (`planning_runs.id`), Indexed | Planning run reference |
| `sku_id` | UUID | No | Foreign Key (`skus.id`), Indexed | Starved SKU |
| `location_id` | UUID | No | Foreign Key (`locations.id`), Indexed | Deficit facility |
| `week_bucket` | VARCHAR(16) | No | Indexed | Projected stockout week |
| `projected_deficit_qty`| INTEGER | No | Check: `> 0` | Deficit units below safety stock |
| `severity` | VARCHAR(32) | No | Indexed: `CRITICAL` (PAB < 0), `WARNING` (PAB < SS) | Deficit severity level |
| `priority_score` | NUMERIC(5, 2) | No | Default: `0.00`, Check: `0 <= score <= 100` | Prioritization score (0-100) |
| `status` | VARCHAR(32) | No | Indexed: `DETECTED`, `ACKNOWLEDGED`, `MITIGATED`, `RESOLVED`, `IGNORED` | Shortage handling state |
| `created_at` | TIMESTAMPTZ | No | Default: `CURRENT_TIMESTAMP` | Audit creation timestamp (UTC) |
| `updated_at` | TIMESTAMPTZ | No | Default: `CURRENT_TIMESTAMP` | Audit modification timestamp (UTC) |

*Unique Constraint:* `(planning_run_id, sku_id, location_id, week_bucket)`.

### 5.3 `mitigation_options` (Solver Recommendations)
Mathematically optimal mitigation actions proposed by OR-Tools.

| Column | Type | Nullable | Constraints / Default | Description |
|---|---|---|---|---|
| `id` | UUID | No | Primary Key | Internal surrogate key |
| `business_id` | VARCHAR(64) | No | Unique, Indexed | Deterministic business ID |
| `shortage_id` | UUID | No | Foreign Key (`shortages.id`), Indexed | Target shortage |
| `action_type` | VARCHAR(32) | No | Indexed: `EXPEDITE_PO`, `ALTERNATE_SUPPLIER`, etc. | Mitigation lever |
| `status` | VARCHAR(32) | No | Indexed: `PROPOSED`, `UNDER_REVIEW`, `APPROVED`, `REJECTED`, `EXPIRED` | Recommendation state |
| `recommended_qty`| INTEGER | No | Check: `> 0` | Suggested volume to mitigate |
| `source_reference_id`| VARCHAR(128) | Yes | - | Reference to PO, Supplier, or Transfer |
| `incremental_cost` | NUMERIC(14, 2) | No | Default: `0.00`, Check: `>= 0` | Financial cost of executing action |
| `service_gain_score`| NUMERIC(5, 2) | No | Default: `100.00`, Check: `0 <= score <= 100` | Estimated OTIF / service protection |
| `roi_ratio` | NUMERIC(10, 4) | No | Default: `0.0000` | Protected margin / incremental cost |
| `rank` | INTEGER | No | Default: `1`, Check: `>= 1` | Solvers preference rank (1 = best) |
| `details_json` | TEXT | Yes | - | Detailed parameters and trade-offs |
| `created_at` | TIMESTAMPTZ | No | Default: `CURRENT_TIMESTAMP` | Audit creation timestamp (UTC) |
| `updated_at` | TIMESTAMPTZ | No | Default: `CURRENT_TIMESTAMP` | Audit modification timestamp (UTC) |

*Unique Constraint:* `(shortage_id, rank)`.

### 5.4 `mitigation_decisions` (Planner Governance Decisions)
Human-in-the-loop decisions approving, overriding, or rejecting mitigations.

| Column | Type | Nullable | Constraints / Default | Description |
|---|---|---|---|---|
| `id` | UUID | No | Primary Key | Internal surrogate key |
| `business_id` | VARCHAR(64) | No | Unique, Indexed | Deterministic business ID |
| `mitigation_option_id`| UUID | No | Foreign Key (`mitigation_options.id`), Indexed | Approved/rejected option |
| `planner_id` | VARCHAR(64) | No | Indexed | SCM planner username or ID |
| `decision` | VARCHAR(32) | No | Indexed: `APPROVED`, `REJECTED`, `OVERRIDDEN` | Final decision |
| `override_qty` | INTEGER | Yes | Check: `override_qty > 0` | Adjusted volume (if overridden) |
| `reason` | TEXT | No | - | Business justification / rationale |
| `decided_at` | TIMESTAMPTZ | No | - | Decision timestamp (UTC) |
| `created_at` | TIMESTAMPTZ | No | Default: `CURRENT_TIMESTAMP` | Audit creation timestamp (UTC) |
| `updated_at` | TIMESTAMPTZ | No | Default: `CURRENT_TIMESTAMP` | Audit modification timestamp (UTC) |

### 5.5 `audit_events` (System-Wide Audit Ledger)
Append-only immutable record of all state transitions and human interventions.

| Column | Type | Nullable | Constraints / Default | Description |
|---|---|---|---|---|
| `id` | UUID | No | Primary Key | Internal surrogate key |
| `business_id` | VARCHAR(64) | No | Unique, Indexed | Deterministic business ID |
| `entity_name` | VARCHAR(64) | No | Indexed | Table or entity modified |
| `entity_id` | VARCHAR(128) | No | Indexed | Primary key of modified entity |
| `action` | VARCHAR(32) | No | Indexed: `CREATE`, `UPDATE`, `APPROVE`, `REJECT` | Action performed |
| `performed_by` | VARCHAR(64) | No | Indexed | User ID or system process name |
| `before_state_json`| TEXT | Yes | - | JSON serialized state before change |
| `after_state_json` | TEXT | Yes | - | JSON serialized state after change |
| `created_at` | TIMESTAMPTZ | No | Default: `CURRENT_TIMESTAMP` | Timestamp of event (UTC) |


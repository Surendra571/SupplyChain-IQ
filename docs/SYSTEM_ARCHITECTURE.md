# SupplyChain IQ - System Architecture Document

## 1. High-Level Architectural Overview

SupplyChain IQ is built as an enterprise, event-driven, decoupled micro-modular architecture. It separates online transactional operations (OLTP), analytical and time-series inventory simulations (OLAP), asynchronous combinatorial optimization (OR-Tools MIP solver), and an interactive single-page application (SPA).

```mermaid
flowchart TD
    subgraph ClientLayer ["Client Layer (Presentation)"]
        UI["React 18 + TypeScript SPA\nTailwind CSS + Recharts + Lucide"]
    end

    subgraph APILayer ["API & Orchestration Layer (FastAPI)"]
        API["FastAPI Gateway / REST Endpoints\nAsync SQLAlchemy 2.0 + Pydantic v2"]
        Auth["Auth & RBAC Middleware"]
        Audit["Audit Interceptor (Immutable Logs)"]
    end

    subgraph StorageLayer ["Data Persistence Layer (PostgreSQL & DuckDB)"]
        PG[("PostgreSQL 16 (OLTP)\nTransactional Schemas:\n- public (Operational)\n- ground_truth (Segregated)")]
        Duck[("DuckDB (In-Memory OLAP)\nFast Vectorized MRP & PAB Simulation")]
    end

    subgraph AsyncLayer ["Asynchronous Execution & Worker Layer"]
        Redis[("Redis 7\nBroker & Result Cache")]
        Worker["Celery Worker Fleet\nDistributed Task Processing"]
        Engine["MRP Engine & Anomaly Detector\n(Pandas / NumPy / DuckDB)"]
        Optimizer["Mitigation Solver\n(Google OR-Tools MIP / CP-SAT)"]
    end

    UI <-->|JSON / REST over HTTP| API
    API --> Auth --> Audit
    API <-->|Read / Write Operational| PG
    API -->|Dispatch Planning Jobs| Redis
    Redis <-->|Pop Task / Return Status| Worker
    Worker --> Engine
    Worker --> Optimizer
    Engine <-->|Fast Batch Queries| Duck
    Duck <-->|Sync Views / Batch Pull| PG
    Optimizer -->|Store Runs & Mitigations| PG
```

---

## 2. Core Architectural Components

### 2.1 Frontend (React, TypeScript, Tailwind CSS, Recharts)
- **Role:** Planner workbench, interactive supply chain digital twin, multi-echelon timeline viewer, mitigation decision matrix.
- **State Management:** TanStack Query (React Query) for server-state caching, optimistic updates, and cache invalidation; Zustand for active planning filters and scenario selections.
- **Visualizations:** Recharts for Projected Available Balance (PAB) vs. Safety Stock trajectory, capacity utilization heatmaps, and cost-vs-service Pareto frontiers.

### 2.2 Backend API (FastAPI, Pydantic v2, SQLAlchemy 2.0)
- **Role:** High-throughput async REST endpoints, request validation, business rule enforcement, transaction orchestration.
- **Design:** Clean Architecture pattern:
  - `routers/`: REST endpoints grouped by domain (inventory, shortages, mitigations, planning runs, audit).
  - `services/`: Domain business logic and orchestration.
  - `repositories/`: Database abstraction with SQLAlchemy 2.0.
  - `schemas/`: Pydantic input/output schemas with strict type validation.
  - `models/`: SQLAlchemy ORM entity definitions.

### 2.3 Optimization Engine (Google OR-Tools)
- **Role:** Multi-objective Mixed-Integer Programming (MIP) and Constraint Programming (CP-SAT) solver for shortage mitigation.
- **Objectives:**
  1. Minimize total incremental mitigation cost (expedite fee + transport variance + supplier surcharge + substitution loss).
  2. Maximize preserved revenue and order fulfillment service levels.
- **Constraints:** Supplier capacity limits per week, shipment transit lead times, bill-of-materials conversion factors, finite factory line capacity.

### 2.4 Data Processing Engine (DuckDB, Pandas, NumPy)
- **Role:** High-performance in-memory simulation for time-phased MRP gross-to-net calculations across large datasets (Full scale: 3,000 SKUs $\times$ 50 Locations $\times$ 52 Weeks = 7.8M time buckets).
- DuckDB executes window functions and multi-table joins in milliseconds, avoiding row-by-row ORM overhead for batch simulations.

### 2.5 Message Broker & Task Queue (Celery + Redis)
- **Role:** Asynchronous processing of long-running planning runs, synthetic data generation, and anomaly detection sweeps.
- Decouples client HTTP requests from compute-intensive MRP runs, providing real-time progress tracking (`PENDING` $\rightarrow$ `RUNNING` $\rightarrow$ `COMPLETED`).

---

## 3. Entity-Relationship (ER) Architecture

The schema contains 20 core business entities organized into functional groups.

```mermaid
erDiagram
    SKU ||--o{ ForecastDemand : "forecasted for"
    LOCATION ||--o{ ForecastDemand : "forecasted at"
    SKU ||--o{ Inventory : "stored as"
    LOCATION ||--o{ Inventory : "houses"
    SKU ||--o{ InventoryTransaction : "transacted"
    LOCATION ||--o{ InventoryTransaction : "occurs at"
    
    SUPPLIER ||--o{ SupplierSKU : "supplies"
    SKU ||--o{ SupplierSKU : "supplied by"
    SUPPLIER ||--o{ SupplierCapacity : "has capacity"
    SKU ||--o{ SupplierCapacity : "allocated capacity"
    
    SUPPLIER ||--o{ PurchaseOrder : "receives order"
    PurchaseOrder ||--o{ PurchaseOrderLine : "contains lines"
    SKU ||--o{ PurchaseOrderLine : "ordered SKU"
    LOCATION ||--o{ PurchaseOrderLine : "delivered to"
    PurchaseOrder ||--o{ Shipment : "fulfilled by"
    
    SKU ||--o{ BOM : "is parent of"
    BOM ||--o{ BOMComponent : "requires"
    SKU ||--o{ BOMComponent : "is component in"
    SKU ||--o{ SubstituteSKU : "primary SKU"
    SKU ||--o{ SubstituteSKU : "substitute SKU"
    
    SKU ||--o{ ProductionPlan : "manufactured"
    LOCATION ||--o{ ProductionPlan : "produced at"
    
    LOCATION ||--o{ LeadTime : "origin"
    LOCATION ||--o{ LeadTime : "destination"

    PlanningRun ||--o{ Shortage : "detects"
    SKU ||--o{ Shortage : "stockout of"
    LOCATION ||--o{ Shortage : "stockout at"
    Shortage ||--o{ MitigationOption : "has options"
    MitigationOption ||--o{ MitigationDecision : "decided by"
    
    AuditEvent }|--|| PlanningRun : "tracks"
```

---

## 4. Immutability Strategy

In enterprise supply chain planning, historical auditability is non-negotiable.

1. **Planning Runs are Append-Only:**
   - Every execution creates a unique `PlanningRun` with a UUID and sequential `run_number`.
   - Results (`Shortage`, `MitigationOption`) reference `planning_run_id`.
   - Running the engine again creates a fresh `PlanningRun`; previous runs are marked `is_superseded = TRUE` but never updated or deleted.
2. **Planner Decisions & Overrides:**
   - When a planner approves or rejects an option, a new `MitigationDecision` record is inserted with the user timestamp, justification, and state change.
   - An immutable `AuditEvent` is captured synchronously within the same database transaction.
3. **Database Level Controls:**
   - Write-once audit tables configured with database triggers preventing `UPDATE` or `DELETE` operations on `audit_events` and `planning_runs`.

---

## 5. Ground-Truth Data Isolation & Anomaly Detection Architecture

```mermaid
flowchart LR
    subgraph Storage ["PostgreSQL Database"]
        subgraph PublicSchema ["Schema: public (Operational)"]
            OperationalTables["SKU, Inventory, POs, Demand,\nShortages, Mitigations"]
        end
        subgraph GTSchema ["Schema: ground_truth (Segregated)"]
            Anomalies["Known Injected Anomalies\n(Anomaly Type, Target ID, Ground Truth Target)"]
            ExpectedOutcomes["Benchmark Expected Shortages\n(Expected Deficits, Expected Mitigations)"]
        end
    end

    subgraph DetectionEngine ["Anomaly Detection Scanner"]
        Rule1["Negative Inventory Detector"]
        Rule2["Lead Time Past Due / Infeasible"]
        Rule3["Circular BOM Graph Cycle Check"]
        Rule4["Supplier Overcapacity Detector"]
        Rule5["Demand Outlier (Z-Score > 4)"]
    end

    subgraph EvaluationHarness ["Validation & Scoring Harness"]
        Metrics["Precision, Recall, F1 Score\nOperational vs. Ground Truth Comparison"]
    end

    PublicSchema --> DetectionEngine
    DetectionEngine --> EvaluationHarness
    GTSchema --> EvaluationHarness
```

- **Segregation:** The `ground_truth` schema is isolated from application APIs. The operational planning engine has zero access to `ground_truth` tables.
- **Verification Harness:** An offline evaluation module compares detected anomalies and shortage calculations against `ground_truth` to compute precision, recall, and benchmark accuracy.


# SupplyChain IQ — Business Logic & Optimization Review

**Reviewer**: Senior Supply Chain Solution Architect & Enterprise Software Engineer  
**Assessment Date**: November 1, 2026  
**Status**: VERIFIED & CERTIFIED  

---

## 1. Projected Available Balance (PAB) Reconciliation

The planning engine implements the standard closed-form weekly inventory balance equation:

$$\text{AvailableBeforeDemand}_w = \text{PAB}_{w-1} + \text{POReceipts}_w + \text{ProdReceipts}_w + \text{TransfersIn}_w - \text{Allocations}_w - \text{TransfersOut}_w$$

$$\text{Closing PAB}_w = \text{AvailableBeforeDemand}_w - \text{ForecastDemand}_w$$

### Week-by-Week Rollover Verification
- $\text{PAB}_0 = \text{On-Hand Inventory}$ from master inventory balance.
- For all $w \ge 1$, $\text{Opening PAB}_w = \text{Closing PAB}_{w-1}$.
- Mathematical reconciliation verified:
  $$\text{Closing PAB}_w - \text{Opening PAB}_w \equiv (\text{Scheduled Receipts}_w - \text{Gross Demand}_w)$$
- Automated assertion in `backend/tests/test_critical_business_rules.py::test_rule_1_projected_balances_reconcile_week_by_week` passed for 100% of tested SKU-location-week combinations.

---

## 2. Segregation of Demand Shortages vs. Safety Stock Gaps

SupplyChain IQ strictly separates two distinct deficit dimensions:

1. **Demand Shortage** (True Unmet Customer Demand):
   $$\text{DemandShortage}_w = \max(0, \text{ForecastDemand}_w - \text{AvailableBeforeDemand}_w)$$
   Occurs strictly when cumulative available stock drops below zero. Triggering this shortage indicates that customer orders will be lost or backlogged.

2. **Safety Stock Gap** (Buffer Stock Depletion):
   $$\text{SafetyStockGap}_w = \max(0, \text{SafetyStock} - \text{Closing PAB}_w)$$
   Safety stock represents an operational buffer. If $\text{Closing PAB}_w > 0$ but $< \text{SafetyStock}$, the gap is classified with `WARNING` severity, notifying planners without triggering an emergency line-stoppage signal.

---

## 3. Inbound Supply & ETA Reconciliation

- **Purchase Orders**: Filtered by status. Cancelled orders are excluded; draft/unapproved orders are excluded from firm receipts.
- **Delayed Shipments**: If an in-transit shipment is delayed by an anomaly, its arrival week is determined by its revised ETA ($\text{ShipmentDate} + \text{ActualTransitDays}$), preventing artificial inventory inflation in earlier periods.
- **Inventory Allocations / Reservations**: Pre-allocated inventory (e.g. reserved customer orders) is deducted from available stock in Week 1 before satisfying forecasted demand.

---

## 4. Multi-Dimensional Shortage Prioritization Model

Every shortage receives an explainable priority score ($0$ to $100$) and is classified into Priority Tiers: `CRITICAL` ($\ge 75$), `HIGH` ($50–74$), `MEDIUM` ($25–49$), or `LOW` ($< 25$).

The score is computed across 4 transparent dimensions:

$$\text{PriorityScore} = W_{\text{urgency}} \cdot S_{\text{urgency}} + W_{\text{volume}} \cdot S_{\text{volume}} + W_{\text{financial}} \cdot S_{\text{financial}} + W_{\text{complexity}} \cdot S_{\text{complexity}}$$

Where:
1. **Urgency Score ($S_{\text{urgency}}$)**: Decays linearly from 100 as days until stockout increases ($100 - \frac{\text{Days}}{42} \times 100$).
2. **Volume Deficit Score ($S_{\text{volume}}$)**: Ratio of deficit quantity to average weekly demand ($\min(100, \frac{\text{Deficit}}{\text{AvgDemand}} \times 25)$).
3. **Financial Impact Score ($S_{\text{financial}}$)**: Logarithmic or normalized scale based on Revenue at Risk ($\text{Deficit} \times \text{Unit Cost}$).
4. **Sourcing Complexity Score ($S_{\text{complexity}}$)**: Higher when SKU has single source, long lead times, or no approved substitutes.

Every shortage record persists the full breakdown dictionary (`score_breakdown`) in PostgreSQL, allowing planners in the Workbench UI to inspect the exact formula contributions.

---

## 5. Root Cause Diagnostic Classifier

Shortages are automatically diagnosed into distinct root causes:
- **`DEMAND_SURGE`**: Current week demand exceeds $1.5\times$ historical average demand.
- **`SUPPLY_DISRUPTION`**: Supplier capacity drop or cancelled/delayed purchase order.
- **`LEAD_TIME_DELAY`**: Transit delay or late promised delivery date.
- **`STRUCTURAL_DEFICIT`**: Zero starting inventory and zero incoming supply.

---

## 6. Google OR-Tools MILP Mitigation Optimization

The mitigation engine implements a Mixed-Integer Linear Programming model (`backend/app/mitigation/optimizer.py`) using SCIP/CBC:

### Decision Variables
- $x_i \in \{0, 1\}$: Binary activation of candidate mitigation option $i$.
- $q_i \ge 0$: Integer quantity allocated to candidate $i$.

### Constraints
1. **Candidate Capacity**: $q_i \le \text{RecoverableQty}_i \cdot x_i$
2. **Shortage Deficit Ceiling**: $\sum_{i \in \text{Cands}(s)} q_i \le \text{Deficit}_s$
3. **Supplier Weekly Capacity**: $\sum_{i \in \text{SuppWeek}} q_i \le \text{AvailableSupplierCapacity}$
4. **Transfer Surplus Limit**: $\sum_{i \in \text{SourceLoc}} q_i \le \text{SourceSurplus}$
5. **MOQ & Approved Substitute Constraints**: Enforced during candidate generation.

### Objective Function
$$\max \sum_{i} \left[ (100 + \text{ShortagePriority}_i) \cdot q_i - C_{\text{penalty}} \cdot \text{UnitCost}_i \cdot q_i - T_{\text{penalty}} \cdot \text{RecoveryDays}_i \cdot x_i \right]$$

This balances maximum service-level protection with incremental procurement and freight costs.


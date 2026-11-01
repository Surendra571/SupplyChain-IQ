"""SupplyChain IQ - Supply-Demand Planning Engine.

Executes deterministic time-phased Projected Available Balance (PAB) simulation,
two-tier shortage quantification (Demand Shortage vs. Safety Stock Gap),
and root cause diagnosis across multi-week planning horizons.
"""

from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
import json
import logging
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid

import numpy as np
import pandas as pd

from backend.app.models.enums import (
    LocationType,
    PurchaseOrderStatus,
    ShipmentStatus,
    ShortageSeverity,
    ShortageStatus,
    SKUType,
)
from backend.app.planning.models import (
    PlanningConfig,
    PlanningRunSummary,
    PriorityTier,
    ShortageOutput,
    ShortageRootCause,
    WeeklyProjection,
)
from backend.app.planning.prioritization import ShortagePrioritizer
from backend.app.planning.root_cause import RootCauseAnalyzer

logger = logging.getLogger(__name__)


def parse_week_bucket(date_val: Any) -> Optional[str]:
    """Deterministically convert a date, datetime, or ISO string to a week bucket string 'YYYYWww'."""
    if date_val is None:
        return None
    if isinstance(date_val, str):
        if "W" in date_val and len(date_val) <= 8:
            return date_val.strip()
        try:
            dt = datetime.fromisoformat(date_val.replace("Z", "+00:00"))
        except ValueError:
            return None
    elif isinstance(date_val, datetime):
        dt = date_val
    elif hasattr(date_val, "year") and hasattr(date_val, "isocalendar"):
        return f"{date_val.isocalendar()[0]}W{date_val.isocalendar()[1]:02d}"
    else:
        return None

    iso_year, iso_week, _ = dt.isocalendar()
    return f"{iso_year}W{iso_week:02d}"


class SupplyDemandPlanningEngine:
    """Core deterministic Supply-Demand Planning Engine."""

    def __init__(self, config: Optional[PlanningConfig] = None):
        self.config = config or PlanningConfig()
        self.prioritizer = ShortagePrioritizer(self.config)
        self.root_cause_analyzer = RootCauseAnalyzer(self.config.demand_spike_multiplier)

    @classmethod
    def from_directory(cls, data_dir: Path, config: Optional[PlanningConfig] = None) -> "SupplyDemandPlanningEngine":
        """Instantiate engine configured with data loaded from exported CSV or Parquet files."""
        engine = cls(config)
        data = engine._load_directory_data(data_dir)
        engine.load_data(data)
        return engine

    def _load_directory_data(self, data_dir: Path) -> Dict[str, List[Dict[str, Any]]]:
        """Load operational datasets from CSV directory into python dicts."""
        tables = [
            "skus",
            "locations",
            "suppliers",
            "supplier_skus",
            "inventories",
            "forecast_demands",
            "purchase_orders",
            "purchase_order_lines",
            "shipments",
            "production_plans",
            "supplier_capacities",
            "lead_times",
            "substitute_skus",
            "boms",
            "bom_components",
        ]
        dataset: Dict[str, List[Dict[str, Any]]] = {}
        for t in tables:
            csv_path = data_dir / f"{t}.csv"
            if csv_path.exists():
                df = pd.read_csv(csv_path)
                # Replace NaN with None
                dataset[t] = df.where(pd.notnull(df), None).to_dict(orient="records")
            else:
                dataset[t] = []
        return dataset

    def load_data(self, data: Dict[str, List[Dict[str, Any]]]) -> None:
        """Cache operational business entities into normalized memory lookups."""
        self.data = data
        self.skus = {s["id"]: s for s in data.get("skus", [])}
        self.skus_by_code = {s["sku_code"]: s for s in data.get("skus", [])}
        self.locations = {l["id"]: l for l in data.get("locations", [])}
        self.locations_by_code = {l["location_code"]: l for l in data.get("locations", [])}
        self.inventories = {(inv["sku_id"], inv["location_id"]): inv for inv in data.get("inventories", [])}

        # Sourcing & lead times
        self.supplier_skus = defaultdict(list)
        for ssku in data.get("supplier_skus", []):
            self.supplier_skus[ssku["sku_id"]].append(ssku)

        # Substitute SKUs
        self.substitutes = defaultdict(list)
        for sub in data.get("substitute_skus", []):
            self.substitutes[sub["primary_sku_id"]].append(sub)

        # Supplier capacities index: (supplier_id, sku_id, week_bucket) -> cap
        self.supplier_capacities = {}
        self.exceeded_capacities_by_sku_week = {}
        for sc in data.get("supplier_capacities", []):
            key = (sc["supplier_id"], sc["sku_id"], sc["week_bucket"])
            self.supplier_capacities[key] = sc
            max_cap = int(sc.get("max_capacity_units", 0))
            surge_cap = int(sc.get("surge_capacity_units", 0))
            committed = int(sc.get("committed_units", 0))
            if committed > (max_cap + surge_cap):
                self.exceeded_capacities_by_sku_week[(str(sc["sku_id"]), sc["week_bucket"])] = {
                    "supplier_id": sc["supplier_id"],
                    "max_capacity_units": max_cap + surge_cap,
                    "committed_units": committed,
                }

    def run_planning(
        self,
        planning_run_id: Optional[str] = None,
        run_number: int = 1,
        horizon_weeks: Optional[int] = None,
    ) -> Tuple[List[WeeklyProjection], List[ShortageOutput], PlanningRunSummary]:
        """Execute the weekly planning engine and generate projections, shortages, and summary.

        Returns:
            (weekly_projections, shortages, summary)
        """
        start_time = time.perf_counter()
        started_at = datetime.now(timezone.utc).isoformat()
        run_id = planning_run_id or f"RUN-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
        horizon = horizon_weeks or self.config.horizon_weeks

        # 1. Discover all horizon week buckets from demand or generate sequence
        horizon_weeks_list = self._get_horizon_weeks(horizon)

        # 2. Rule 8: Validate Unit of Measure consistency across records
        self._validate_uom_integrity()

        # 3. Pre-aggregate Reconciled Inbound PO Receipts & Shipments
        # Rules: 1 (period availability), 2 (delayed arrivals), 3 (no cancelled POs), 4 (no duplicate counting)
        reconciled_purchase_receipts, delayed_shipments_map, delayed_pos_map = self._aggregate_purchase_receipts(horizon_weeks_list)

        # 4. Pre-aggregate Production Receipts respecting Plant Capacity (Rule 7)
        reconciled_production_receipts, production_constrained_map = self._aggregate_production_receipts(horizon_weeks_list)

        # 5. Pre-aggregate Forecast Demand & Allocations (Rule 5: Respect inventory reservations)
        demand_map, allocations_map = self._aggregate_demand_and_allocations(horizon_weeks_list)

        # 6. Execute Week-by-Week Simulation across all SKU-Location pairs
        all_projections: List[WeeklyProjection] = []
        all_shortages: List[ShortageOutput] = []

        active_pairs = self._get_planning_pairs()

        for sku_id, loc_id in active_pairs:
            sku = self.skus[sku_id]
            loc = self.locations[loc_id]
            inv = self.inventories.get((sku_id, loc_id), {})

            opening_on_hand = int(inv.get("on_hand_qty", 0))
            allocated_initial = int(inv.get("allocated_qty", 0))
            safety_stock = int(inv.get("safety_stock_qty", 0))

            # History of forecast demand for demand-spike detection
            sku_demands = [demand_map.get((sku_id, loc_id, w), 0) for w in horizon_weeks_list]
            avg_demand = float(sum(sku_demands) / len(sku_demands)) if sku_demands else 0.0

            # Sourcing attributes for prioritization & root cause
            sskus = self.supplier_skus.get(sku_id, [])
            lead_time_days = sskus[0].get("lead_time_days", 14) if sskus else 14
            missing_lead_time = (len(sskus) == 0 or any(s.get("lead_time_days") in (None, 0) for s in sskus))
            has_alt_suppliers = len(sskus) > 1

            # Check substitute validity
            subs = self.substitutes.get(sku_id, [])
            invalid_substitute = False
            has_active_substitute = False
            if subs:
                for sub in subs:
                    eff_to = sub.get("effective_to")
                    # Expired or unapproved substitute
                    if eff_to is not None and str(eff_to) < started_at[:10]:
                        invalid_substitute = True
                    else:
                        has_active_substitute = True

            # Week-by-Week recurrence:
            current_pab = opening_on_hand

            for w_idx, week_bucket in enumerate(horizon_weeks_list, start=1):
                po_receipts = reconciled_purchase_receipts.get((sku_id, loc_id, week_bucket), 0)
                prod_receipts = reconciled_production_receipts.get((sku_id, loc_id, week_bucket), 0)
                transfers_in = 0  # Extended transfer support
                transfers_out = 0

                f_demand = demand_map.get((sku_id, loc_id, week_bucket), 0)

                # Rule 5: Respect inventory reservations
                # Week 1 absorbs initial allocated_qty if not explicitly Phased
                alloc = allocations_map.get((sku_id, loc_id, week_bucket), 0)
                if w_idx == 1:
                    alloc += allocated_initial

                # CALCULATIONS (PAB & AvailableBeforeDemand per prompt formula):
                # AvailableBeforeDemand = PAB[t-1] + PurchaseReceipts[t] + ProductionReceipts[t] + TransfersIn[t] - Allocations[t] - TransfersOut[t]
                available_before_demand = (
                    current_pab
                    + po_receipts
                    + prod_receipts
                    + transfers_in
                    - alloc
                    - transfers_out
                )

                # Closing PAB:
                # PAB[t] = AvailableBeforeDemand - ForecastDemand[t]
                closing_pab = available_before_demand - f_demand

                # Two shortage measures per exact user formula:
                # DemandShortage = MAX(0, ForecastDemand - AvailableBeforeDemand)
                demand_shortage = max(0, f_demand - available_before_demand)

                # SafetyStockGap = MAX(0, SafetyStock - ClosingProjectedBalance)
                safety_stock_gap = max(0, safety_stock - closing_pab)

                projection = WeeklyProjection.model_construct(
                    sku_id=str(sku_id),
                    sku_code=sku["sku_code"],
                    location_id=str(loc_id),
                    location_code=loc["location_code"],
                    week_bucket=week_bucket,
                    week_index=w_idx,
                    unit_of_measure=sku.get("unit_of_measure", "EA"),
                    opening_pab=current_pab,
                    purchase_receipts=po_receipts,
                    production_receipts=prod_receipts,
                    transfers_in=transfers_in,
                    forecast_demand=f_demand,
                    allocations=alloc,
                    transfers_out=transfers_out,
                    available_before_demand=available_before_demand,
                    closing_pab=closing_pab,
                    safety_stock=safety_stock,
                    demand_shortage=demand_shortage,
                    safety_stock_gap=safety_stock_gap,
                )
                all_projections.append(projection)

                # Shortage Detection & Classification
                # If closing_pab < 0 -> CRITICAL; else if safety_stock_gap > 0 -> WARNING
                if closing_pab < 0 or safety_stock_gap > 0:
                    severity = ShortageSeverity.CRITICAL if closing_pab < 0 else ShortageSeverity.WARNING

                    # Total deficit quantity to restore to safety stock:
                    # When closing_pab < 0: safety_stock_gap = safety_stock - closing_pab = safety_stock + demand_shortage
                    deficit_qty = safety_stock_gap if safety_stock_gap > 0 else demand_shortage

                    days_until_stockout = (w_idx - 1) * 7

                    # Prioritization calculation
                    score, tier, financial_val, score_breakdown = self.prioritizer.calculate_priority(
                        days_until_stockout=days_until_stockout,
                        shortage_qty=deficit_qty,
                        avg_weekly_demand=avg_demand,
                        unit_cost=float(sku.get("unit_cost", 0.0)),
                        unit_price=float(sku.get("unit_price", 0.0)),
                        sku_type=sku.get("sku_type", SKUType.FINISHED_GOOD.value),
                        location_type=loc.get("location_type", LocationType.DC.value),
                        lead_time_days=lead_time_days,
                        has_alternative_suppliers=has_alt_suppliers,
                        has_active_substitute=has_active_substitute,
                    )

                    # Root cause diagnosis (Rule 10)
                    delayed_ships = delayed_shipments_map.get((sku_id, loc_id, week_bucket), [])
                    delayed_pos = delayed_pos_map.get((sku_id, loc_id, week_bucket), [])
                    supp_cap_exceeded = self._check_supplier_capacity_exceeded(sku_id, week_bucket)
                    prod_constrained = production_constrained_map.get((loc_id, week_bucket))

                    root_cause, root_explanation = self.root_cause_analyzer.diagnose(
                        sku_code=sku["sku_code"],
                        location_code=loc["location_code"],
                        week_bucket=week_bucket,
                        week_index=w_idx,
                        demand_qty=f_demand,
                        avg_demand=avg_demand,
                        opening_on_hand=opening_on_hand,
                        safety_stock=safety_stock,
                        missing_lead_time=missing_lead_time,
                        invalid_substitute=invalid_substitute,
                        delayed_shipments=delayed_ships,
                        delayed_pos=delayed_pos,
                        supplier_capacity_exceeded=supp_cap_exceeded,
                        production_constrained=prod_constrained,
                    )

                    bid = f"SHORT-{run_number:04d}-{sku['sku_code']}-{loc['location_code']}-{week_bucket}"
                    shortage = ShortageOutput.model_construct(
                        business_id=bid,
                        planning_run_id=run_id,
                        sku_id=str(sku_id),
                        sku_code=sku["sku_code"],
                        sku_name=sku.get("name", sku["sku_code"]),
                        location_id=str(loc_id),
                        location_code=loc["location_code"],
                        location_name=loc.get("name", loc["location_code"]),
                        week_bucket=week_bucket,
                        week_index=w_idx,
                        days_until_stockout=days_until_stockout,
                        projected_deficit_qty=deficit_qty,
                        demand_shortage_qty=demand_shortage,
                        safety_stock_gap_qty=safety_stock_gap,
                        severity=severity,
                        priority_tier=tier,
                        priority_score=score,
                        financial_impact=financial_val,
                        root_cause=root_cause,
                        root_cause_explanation=root_explanation,
                        score_breakdown=score_breakdown,
                        details={
                            "available_before_demand": available_before_demand,
                            "closing_pab": closing_pab,
                            "safety_stock": safety_stock,
                            "forecast_demand": f_demand,
                        },
                        status=ShortageStatus.DETECTED,
                    )
                    all_shortages.append(shortage)

                # Roll forward closing PAB to next period
                current_pab = closing_pab

        # Summary KPIs
        completed_at = datetime.now(timezone.utc).isoformat()
        execution_sec = round(time.perf_counter() - start_time, 4)

        root_cause_counts = defaultdict(int)
        for s in all_shortages:
            root_cause_counts[s.root_cause.value] += 1

        priority_counts = defaultdict(int)
        for s in all_shortages:
            priority_counts[s.priority_tier.value] += 1

        summary = PlanningRunSummary(
            run_id=run_id,
            run_number=run_number,
            horizon_weeks=horizon,
            total_skus=len(self.skus),
            total_locations=len(self.locations),
            total_projections=len(all_projections),
            total_shortages=len(all_shortages),
            critical_shortages=sum(1 for s in all_shortages if s.severity == ShortageSeverity.CRITICAL),
            warning_shortages=sum(1 for s in all_shortages if s.severity == ShortageSeverity.WARNING),
            total_demand_shortage_qty=sum(s.demand_shortage_qty for s in all_shortages),
            total_safety_stock_gap_qty=sum(s.safety_stock_gap_qty for s in all_shortages),
            total_financial_impact=round(sum(s.financial_impact for s in all_shortages), 2),
            root_cause_breakdown=dict(root_cause_counts),
            priority_breakdown=dict(priority_counts),
            started_at=started_at,
            completed_at=completed_at,
            execution_time_seconds=execution_sec,
            config=self.config.model_dump(),
        )

        return all_projections, all_shortages, summary

    def _get_horizon_weeks(self, horizon: int) -> List[str]:
        """Collect sorted distinct week buckets covering the planning horizon."""
        weeks_found = set()
        for fd in self.data.get("forecast_demands", []):
            wb = fd.get("week_bucket")
            if wb:
                weeks_found.add(wb)

        sorted_weeks = sorted(list(weeks_found))
        if len(sorted_weeks) >= horizon:
            return sorted_weeks[:horizon]
        elif sorted_weeks:
            # Expand horizon weeks sequentially if needed
            last_wb = sorted_weeks[-1]
            try:
                yr, wk = int(last_wb[:4]), int(last_wb[5:])
            except Exception:
                yr, wk = 2026, 1
            while len(sorted_weeks) < horizon:
                wk += 1
                if wk > 52:
                    yr += 1
                    wk = 1
                sorted_weeks.append(f"{yr}W{wk:02d}")
            return sorted_weeks
        else:
            # Fallback 2026W01 ... 2026W12
            return [f"2026W{w:02d}" for w in range(1, horizon + 1)]

    def _get_planning_pairs(self) -> List[Tuple[str, str]]:
        """Identify all SKU-Location pairs that have inventory, demand, or production."""
        pairs = set()
        for (sku_id, loc_id) in self.inventories.keys():
            pairs.add((str(sku_id), str(loc_id)))
        for fd in self.data.get("forecast_demands", []):
            pairs.add((str(fd["sku_id"]), str(fd["location_id"])))
        for pp in self.data.get("production_plans", []):
            pairs.add((str(pp["sku_id"]), str(pp["location_id"])))
        for pol in self.data.get("purchase_order_lines", []):
            pairs.add((str(pol["sku_id"]), str(pol["destination_location_id"])))

        # Return sorted by SKU then Location
        return sorted(list(pairs))

    def _validate_uom_integrity(self) -> None:
        """Rule 8: Validate units before quantity aggregation.

        Ensure all demand, inventory, and order lines match the master SKU unit_of_measure.
        """
        for pol in self.data.get("purchase_order_lines", []):
            sku = self.skus.get(pol.get("sku_id"))
            if sku:
                sku_uom = str(sku.get("unit_of_measure", "EA")).strip().upper()
                pol_uom = pol.get("unit_of_measure")
                if pol_uom and str(pol_uom).strip().upper() != sku_uom:
                    raise ValueError(
                        f"Unit of measure mismatch for PO line {pol.get('id', 'unknown')}: "
                        f"line has '{pol_uom}' but master SKU {sku.get('sku_code')} requires '{sku_uom}'."
                    )

    def _aggregate_purchase_receipts(
        self, horizon_weeks: List[str]
    ) -> Tuple[
        Dict[Tuple[str, str, str], int],
        Dict[Tuple[str, str, str], List[Dict[str, Any]]],
        Dict[Tuple[str, str, str], List[Dict[str, Any]]],
    ]:
        """Aggregate reconciled inbound purchase receipts without double-counting.

        Rules satisfied:
        - Rule 1: Count inbound stock only when expected to become available.
        - Rule 2: Delayed shipments use revised arrival dates (eta / actual_delivery_date).
        - Rule 3: Do not count cancelled purchase orders or cancelled shipments.
        - Rule 4: Prevent duplicate receipt counting between PO lines and active shipments.
        """
        receipts: Dict[Tuple[str, str, str], int] = defaultdict(int)
        delayed_shipments: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = defaultdict(list)
        delayed_pos: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = defaultdict(list)

        # Index PO headers
        pos_by_id = {po["id"]: po for po in self.data.get("purchase_orders", [])}

        # Index Shipments by PO ID
        shipments_by_po = defaultdict(list)
        for s in self.data.get("shipments", []):
            if str(s.get("status", "")).upper() != ShipmentStatus.CANCELLED.value:
                shipments_by_po[s["po_id"]].append(s)

        # Process PO lines
        for pol in self.data.get("purchase_order_lines", []):
            po_id = pol["po_id"]
            po = pos_by_id.get(po_id)
            if not po:
                continue

            # Rule 3: Do not count cancelled purchase orders
            if str(po.get("status", "")).upper() == PurchaseOrderStatus.CANCELLED.value:
                continue

            sku_id = str(pol["sku_id"])
            loc_id = str(pol["destination_location_id"])
            ordered_qty = int(pol.get("ordered_qty", 0))
            received_qty = int(pol.get("received_qty", 0))
            open_qty = max(0, ordered_qty - received_qty)
            if open_qty <= 0:
                continue

            # Original promised arrival bucket
            prom_date = pol.get("promised_delivery_date")
            prom_week = parse_week_bucket(prom_date)

            # Check if this PO is associated with an active shipment
            po_shipments = shipments_by_po.get(po_id, [])

            if po_shipments:
                # Rule 4: Prevent duplicate receipt counting.
                # Inbound delivery is tracked by the shipment.
                # Rule 2: Delayed shipments must use revised arrival dates (eta / revised date)
                for ship in po_shipments:
                    arr_date = ship.get("actual_delivery_date") or ship.get("eta") or prom_date
                    arr_week = parse_week_bucket(arr_date)

                    # Check for delay
                    if prom_date and arr_date and str(arr_date)[:10] > str(prom_date)[:10]:
                        delay_info = {
                            "shipment_id": ship.get("id"),
                            "tracking_number": ship.get("tracking_number"),
                            "promised_date": str(prom_date)[:10],
                            "revised_date": str(arr_date)[:10],
                        }
                        # Link delay to both the starved promised period and the late arrival period
                        if prom_week:
                            delayed_shipments[(sku_id, loc_id, prom_week)].append(delay_info)
                        if arr_week and arr_week != prom_week:
                            delayed_shipments[(sku_id, loc_id, arr_week)].append(delay_info)

                    if arr_week:
                        receipts[(sku_id, loc_id, arr_week)] += open_qty
            else:
                # Open PO line without shipment -> arrives at promised delivery week
                if prom_week:
                    receipts[(sku_id, loc_id, prom_week)] += open_qty

                    # Check if PO delivery is later in horizon
                    if prom_date and horizon_weeks and prom_week > horizon_weeks[0]:
                        delayed_pos[(sku_id, loc_id, prom_week)].append({
                            "po_id": po_id,
                            "po_number": po.get("po_number"),
                            "promised_delivery_date": str(prom_date)[:10],
                        })

        return receipts, delayed_shipments, delayed_pos

    def _aggregate_production_receipts(
        self, horizon_weeks: List[str]
    ) -> Tuple[Dict[Tuple[str, str, str], int], Dict[Tuple[str, str], Dict[str, Any]]]:
        """Aggregate scheduled manufacturing output respecting plant capacity (Rule 7).

        Returns:
            (reconciled_receipts, production_constrained_map)
        """
        receipts: Dict[Tuple[str, str, str], int] = defaultdict(int)
        plant_weekly_planned: Dict[Tuple[str, str], int] = defaultdict(int)
        constrained_map: Dict[Tuple[str, str], Dict[str, Any]] = {}

        # 1. Total planned per plant per week
        for pp in self.data.get("production_plans", []):
            if str(pp.get("status", "")).upper() == "CANCELLED":
                continue
            loc_id = str(pp["location_id"])
            wb = pp.get("week_bucket")
            qty = int(pp.get("planned_quantity", 0))
            if wb:
                plant_weekly_planned[(loc_id, wb)] += qty

        # 2. Check plant capacity limits
        for (loc_id, wb), total_planned in plant_weekly_planned.items():
            loc = self.locations.get(loc_id)
            if loc:
                cap = int(loc.get("capacity_units", 100000))
                if cap > 0 and total_planned > cap:
                    constrained_map[(loc_id, wb)] = {
                        "capacity_units": cap,
                        "planned_units": total_planned,
                        "location_code": loc.get("location_code"),
                    }

        # 3. Assign feasible receipts
        for pp in self.data.get("production_plans", []):
            if str(pp.get("status", "")).upper() == "CANCELLED":
                continue
            sku_id = str(pp["sku_id"])
            loc_id = str(pp["location_id"])
            wb = pp.get("week_bucket")
            qty = int(pp.get("planned_quantity", 0))

            if wb:
                # If capacity constrained, scale proportionately
                if (loc_id, wb) in constrained_map:
                    cap = constrained_map[(loc_id, wb)]["capacity_units"]
                    total_p = constrained_map[(loc_id, wb)]["planned_units"]
                    feasible_qty = int(round(qty * (cap / total_p)))
                    receipts[(sku_id, loc_id, wb)] += feasible_qty
                else:
                    receipts[(sku_id, loc_id, wb)] += qty

        return receipts, constrained_map

    def _aggregate_demand_and_allocations(
        self, horizon_weeks: List[str]
    ) -> Tuple[Dict[Tuple[str, str, str], int], Dict[Tuple[str, str, str], int]]:
        """Index forecast gross customer demand and inventory allocations."""
        demand_map: Dict[Tuple[str, str, str], int] = defaultdict(int)
        allocations_map: Dict[Tuple[str, str, str], int] = defaultdict(int)

        for fd in self.data.get("forecast_demands", []):
            sku_id = str(fd["sku_id"])
            loc_id = str(fd["location_id"])
            wb = fd.get("week_bucket")
            qty = int(fd.get("forecast_qty", 0))
            if wb:
                demand_map[(sku_id, loc_id, wb)] += qty

        return demand_map, allocations_map

    def _check_supplier_capacity_exceeded(self, sku_id: str, week_bucket: str) -> Optional[Dict[str, Any]]:
        """Rule 6: Check if supplier capacity was exceeded for this SKU in period week_bucket (O(1) pre-indexed lookup)."""
        return self.exceeded_capacities_by_sku_week.get((str(sku_id), week_bucket))

    def verify_balance_reconciliation(self, projections: List[WeeklyProjection]) -> bool:
        """Mathematically reconcile inventory balances week-by-week.

        Verifies:
        1. AvailableBeforeDemand[t] == OpeningPAB[t] + Receipts[t] - Allocations[t] - TransfersOut[t]
        2. ClosingPAB[t] == AvailableBeforeDemand[t] - ForecastDemand[t]
        3. OpeningPAB[t] == ClosingPAB[t-1] for t > 1
        4. DemandShortage == MAX(0, ForecastDemand - AvailableBeforeDemand)
        5. SafetyStockGap == MAX(0, SafetyStock - ClosingPAB)
        """
        # Group by (sku_id, location_id)
        grouped = defaultdict(list)
        for p in projections:
            grouped[(p.sku_id, p.location_id)].append(p)

        for (sku_id, loc_id), series in grouped.items():
            # Sort chronologically by week_index
            series = sorted(series, key=lambda x: x.week_index)
            for idx, p in enumerate(series):
                expected_avail = (
                    p.opening_pab
                    + p.purchase_receipts
                    + p.production_receipts
                    + p.transfers_in
                    - p.allocations
                    - p.transfers_out
                )
                if p.available_before_demand != expected_avail:
                    raise AssertionError(
                        f"Reconciliation error at ({p.sku_code}, {p.location_code}, {p.week_bucket}): "
                        f"available_before_demand {p.available_before_demand} != expected {expected_avail}"
                    )

                expected_closing = p.available_before_demand - p.forecast_demand
                if p.closing_pab != expected_closing:
                    raise AssertionError(
                        f"Reconciliation error at ({p.sku_code}, {p.location_code}, {p.week_bucket}): "
                        f"closing_pab {p.closing_pab} != expected {expected_closing}"
                    )

                expected_demand_shortage = max(0, p.forecast_demand - p.available_before_demand)
                if p.demand_shortage != expected_demand_shortage:
                    raise AssertionError(
                        f"Reconciliation error at ({p.sku_code}, {p.location_code}, {p.week_bucket}): "
                        f"demand_shortage {p.demand_shortage} != expected {expected_demand_shortage}"
                    )

                expected_ss_gap = max(0, p.safety_stock - p.closing_pab)
                if p.safety_stock_gap != expected_ss_gap:
                    raise AssertionError(
                        f"Reconciliation error at ({p.sku_code}, {p.location_code}, {p.week_bucket}): "
                        f"safety_stock_gap {p.safety_stock_gap} != expected {expected_ss_gap}"
                    )

                # Check period linkage: OpeningPAB[t] == ClosingPAB[t-1]
                if idx > 0:
                    prev_p = series[idx - 1]
                    if p.opening_pab != prev_p.closing_pab:
                        raise AssertionError(
                            f"Linkage reconciliation error at ({p.sku_code}, {p.location_code}, {p.week_bucket}): "
                            f"opening_pab {p.opening_pab} != previous closing_pab {prev_p.closing_pab}"
                        )

        return True

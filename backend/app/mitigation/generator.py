"""SupplyChain IQ - Candidate Mitigation Generator.

Evaluates all 7 mitigation option types and validates feasibility against
the 9 SCM business rules (supplier approval, capacity, MOQ, lead time,
plant capacity, BOM components, substitute validity, UOM, and safety stock preservation).
"""

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import logging
import math
from typing import Any, Dict, List, Optional, Tuple

from backend.app.models.enums import (
    LocationType,
    MitigationActionType,
    MitigationOptionStatus,
    PurchaseOrderStatus,
    ShipmentStatus,
    SKUType,
)
from backend.app.mitigation.models import MitigationCandidate, MitigationConfig
from backend.app.planning.engine import parse_week_bucket

logger = logging.getLogger(__name__)


def get_date_from_week(week_str: str, day_of_week: int = 1) -> datetime:
    """Deterministically convert 'YYYYWww' to a UTC datetime on the specified day of the week (1=Mon, 4=Thu)."""
    try:
        year = int(week_str[:4])
        week = int(week_str[5:])
        # Jan 4 is always in week 1 in ISO calendar
        first_iso = datetime(year, 1, 4, tzinfo=timezone.utc)
        start_of_w1 = first_iso - timedelta(days=first_iso.isoweekday() - 1)
        target = start_of_w1 + timedelta(weeks=week - 1, days=day_of_week - 1)
        return target
    except Exception:
        return datetime(2026, 1, 1, tzinfo=timezone.utc)


class CandidateGenerator:
    """Generates and evaluates candidate mitigation options for supply shortages."""

    def __init__(self, data: Dict[str, List[Dict[str, Any]]], config: Optional[MitigationConfig] = None):
        self.data = data
        self.config = config or MitigationConfig()
        self._index_data()

    def _index_data(self):
        """Index operational entities for rapid constraint evaluation."""
        self.skus = {s["id"]: s for s in self.data.get("skus", [])}
        self.locations = {l["id"]: l for l in self.data.get("locations", [])}
        self.suppliers = {s["id"]: s for s in self.data.get("suppliers", [])}
        self.inventories = {(inv["sku_id"], inv["location_id"]): inv for inv in self.data.get("inventories", [])}

        # Sourcing catalog
        self.supplier_skus_by_sku = defaultdict(list)
        for ssku in self.data.get("supplier_skus", []):
            self.supplier_skus_by_sku[ssku["sku_id"]].append(ssku)

        # Supplier capacities: (supplier_id, sku_id, week_bucket) -> cap
        self.supplier_capacities = {}
        for sc in self.data.get("supplier_capacities", []):
            key = (sc["supplier_id"], sc["sku_id"], sc["week_bucket"])
            self.supplier_capacities[key] = sc

        # Lead times / transport lanes: (origin_id, dest_id) -> lead_time
        self.lanes = {}
        for lt in self.data.get("lead_times", []):
            key = (lt["origin_location_id"], lt["destination_location_id"])
            self.lanes[key] = lt

        # Substitute SKUs by primary_sku_id
        self.substitutes = defaultdict(list)
        for sub in self.data.get("substitute_skus", []):
            self.substitutes[sub["primary_sku_id"]].append(sub)

        # BOMs and BOM components
        self.boms_by_parent = defaultdict(list)
        for b in self.data.get("boms", []):
            self.boms_by_parent[b["parent_sku_id"]].append(b)

        self.bom_components_by_bom = defaultdict(list)
        for bc in self.data.get("bom_components", []):
            self.bom_components_by_bom[bc["bom_id"]].append(bc)

        # Open PO lines by (sku_id, destination_location_id)
        self.open_po_lines = defaultdict(list)
        pos_by_id = {po["id"]: po for po in self.data.get("purchase_orders", [])}
        for pol in self.data.get("purchase_order_lines", []):
            po = pos_by_id.get(pol["po_id"])
            if po and str(po.get("status", "")).upper() != PurchaseOrderStatus.CANCELLED.value:
                key = (pol["sku_id"], pol["destination_location_id"])
                self.open_po_lines[key].append(pol)

    def generate_candidates(self, shortage: Any, current_date: Optional[datetime] = None) -> List[MitigationCandidate]:
        """Generate all candidate options for a shortage and evaluate feasibility."""
        candidates: List[MitigationCandidate] = []

        now = current_date or datetime(2026, 1, 1, tzinfo=timezone.utc)
        sku_id = str(shortage.sku_id)
        loc_id = str(shortage.location_id)
        target_week = shortage.week_bucket
        deficit = int(shortage.projected_deficit_qty)
        req_date = get_date_from_week(target_week, day_of_week=1)

        sku = self.skus.get(sku_id, {})
        loc = self.locations.get(loc_id, {})
        unit_cost = float(sku.get("unit_cost", 0.0))
        unit_price = float(sku.get("unit_price", unit_cost * 1.5))

        # ---------------------------------------------------------------------
        # 1. Existing Supplier Procurement
        # ---------------------------------------------------------------------
        c_exist = self._eval_supplier_procurement(
            shortage_id=shortage.business_id,
            sku=sku,
            loc=loc,
            target_week=target_week,
            req_date=req_date,
            now=now,
            deficit=deficit,
            is_alternative=False,
        )
        if c_exist:
            candidates.append(c_exist)

        # ---------------------------------------------------------------------
        # 2. Alternative Approved Supplier
        # ---------------------------------------------------------------------
        c_alt = self._eval_supplier_procurement(
            shortage_id=shortage.business_id,
            sku=sku,
            loc=loc,
            target_week=target_week,
            req_date=req_date,
            now=now,
            deficit=deficit,
            is_alternative=True,
        )
        if c_alt:
            candidates.append(c_alt)

        # ---------------------------------------------------------------------
        # 3. Expedited Shipment
        # ---------------------------------------------------------------------
        c_exp = self._eval_expedited_shipment(
            shortage_id=shortage.business_id,
            sku=sku,
            loc=loc,
            target_week=target_week,
            req_date=req_date,
            now=now,
            deficit=deficit,
        )
        if c_exp:
            candidates.append(c_exp)

        # ---------------------------------------------------------------------
        # 4. Inventory Transfer from Another Location
        # ---------------------------------------------------------------------
        c_trans = self._eval_inventory_transfer(
            shortage_id=shortage.business_id,
            sku=sku,
            loc=loc,
            target_week=target_week,
            req_date=req_date,
            now=now,
            deficit=deficit,
        )
        if c_trans:
            candidates.extend(c_trans)

        # ---------------------------------------------------------------------
        # 5. Production Increase (Finished Goods & Subassemblies)
        # ---------------------------------------------------------------------
        c_prod = self._eval_production_increase(
            shortage_id=shortage.business_id,
            sku=sku,
            loc=loc,
            target_week=target_week,
            req_date=req_date,
            now=now,
            deficit=deficit,
        )
        if c_prod:
            candidates.append(c_prod)

        # ---------------------------------------------------------------------
        # 6. Approved Substitute SKU
        # ---------------------------------------------------------------------
        c_sub = self._eval_substitute_sku(
            shortage_id=shortage.business_id,
            sku=sku,
            loc=loc,
            target_week=target_week,
            req_date=req_date,
            now=now,
            deficit=deficit,
        )
        if c_sub:
            candidates.extend(c_sub)

        # ---------------------------------------------------------------------
        # 7. Partial Fulfillment Options
        # ---------------------------------------------------------------------
        # For any feasible candidate that could only partially fulfill the deficit
        for c in list(candidates):
            if c.is_feasible and 0 < c.recoverable_quantity < deficit:
                c_part = MitigationCandidate(
                    candidate_id=f"PART-{c.candidate_id}",
                    shortage_id=shortage.business_id,
                    action_type=MitigationActionType.PARTIAL_FULFILLMENT,
                    status=MitigationOptionStatus.PROPOSED,
                    sku_id=c.sku_id,
                    sku_code=c.sku_code,
                    location_id=c.location_id,
                    location_code=c.location_code,
                    target_week=target_week,
                    recoverable_quantity=c.recoverable_quantity,
                    quantity_still_at_risk=deficit - c.recoverable_quantity,
                    additional_procurement_cost=c.additional_procurement_cost,
                    transportation_cost=c.transportation_cost,
                    production_cost=c.production_cost,
                    total_cost=c.total_cost,
                    expected_arrival_date=c.expected_arrival_date,
                    expected_arrival_week=c.expected_arrival_week,
                    recovery_time_days=c.recovery_time_days,
                    service_level_impact=c.service_level_impact,
                    roi_ratio=c.roi_ratio,
                    is_feasible=True,
                    source_reference_id=c.source_reference_id,
                    explanation=f"Partial fulfillment: Mitigates {c.recoverable_quantity} of {deficit} units via {c.action_type.value}; leaves {deficit - c.recoverable_quantity} units at risk.",
                    details={"underlying_action": c.action_type.value, "original_candidate_id": c.candidate_id},
                )
                candidates.append(c_part)

        return candidates

    def _eval_supplier_procurement(
        self,
        shortage_id: str,
        sku: Dict[str, Any],
        loc: Dict[str, Any],
        target_week: str,
        req_date: datetime,
        now: datetime,
        deficit: int,
        is_alternative: bool,
    ) -> Optional[MitigationCandidate]:
        """Option 1 & 2: Existing Supplier Procurement vs Alternate Approved Supplier."""
        sku_id = sku["id"]
        loc_id = loc["id"]
        sskus = self.supplier_skus_by_sku.get(sku_id, [])

        # Filter by preferred status
        matching = [s for s in sskus if s.get("is_preferred", False) != is_alternative]
        if not matching:
            return None

        ssku = matching[0]
        supp_id = ssku["supplier_id"]
        supp = self.suppliers.get(supp_id, {})
        supp_code = supp.get("supplier_code", "SUP-UNKNOWN")

        action_type = (
            MitigationActionType.ALTERNATIVE_APPROVED_SUPPLIER
            if is_alternative
            else MitigationActionType.EXISTING_SUPPLIER_PROCUREMENT
        )

        infeasibility_reasons = []

        # 1. Supplier must be approved (valid dates)
        eff_from = ssku.get("effective_from")
        eff_to = ssku.get("effective_to")
        now_str = now.isoformat()[:10]
        if eff_from and str(eff_from)[:10] > now_str:
            infeasibility_reasons.append(f"Supplier contract effective from {eff_from} is not yet active.")
        if eff_to and str(eff_to)[:10] < now_str:
            infeasibility_reasons.append(f"Supplier contract expired on {eff_to}.")

        # 2. Lead Time check
        lead_time_days = int(ssku.get("lead_time_days", 14))
        arr_date = now + timedelta(days=lead_time_days)
        arr_week = parse_week_bucket(arr_date)

        if arr_date > req_date and arr_week > target_week:
            infeasibility_reasons.append(
                f"Supplier lead time ({lead_time_days} days) arrives in {arr_week}, after required shortage week {target_week}."
            )

        # 3. Available Capacity check
        sc = self.supplier_capacities.get((supp_id, sku_id, target_week))
        max_cap = int(sc.get("max_capacity_units", 100000)) if sc else 100000
        surge_cap = int(sc.get("surge_capacity_units", 0)) if sc else 0
        committed = int(sc.get("committed_units", 0)) if sc else 0
        available_cap = max(0, (max_cap + surge_cap) - committed)

        if available_cap <= 0:
            infeasibility_reasons.append(
                f"Supplier {supp_code} capacity is exhausted in {target_week} ({committed}/{max_cap + surge_cap} units committed)."
            )

        # 4. MOQ check
        moq = int(ssku.get("moq", 1))
        order_qty = max(deficit, moq)
        if available_cap > 0 and available_cap < moq:
            infeasibility_reasons.append(
                f"Available supplier capacity ({available_cap} units) cannot satisfy Minimum Order Quantity ({moq} units) (MOQ)."
            )

        recoverable_qty = min(deficit, available_cap)
        is_feasible = (len(infeasibility_reasons) == 0 and recoverable_qty > 0)

        # Costs
        contract_price = float(ssku.get("unit_price", sku.get("unit_cost", 10.0)))
        total_procurement_cost = round(order_qty * contract_price, 2)
        total_cost = total_procurement_cost

        # Service Level Impact
        service_gain = round((recoverable_qty / deficit) * 100.0, 2) if deficit > 0 else 100.0

        # Protected Revenue ROI
        revenue_protected = recoverable_qty * float(sku.get("unit_price", contract_price * 1.5))
        roi = round(revenue_protected / max(total_cost, 1.0), 4)

        explanation = (
            f"Procure {order_qty} units from {'secondary' if is_alternative else 'primary'} vendor {supp_code} "
            f"(Lead time: {lead_time_days}d, MOQ: {moq}). Arrives {arr_week}."
        )
        if not is_feasible:
            explanation = f"Infeasible: {'; '.join(infeasibility_reasons)}"

        return MitigationCandidate(
            shortage_id=shortage_id,
            action_type=action_type,
            sku_id=sku_id,
            sku_code=sku["sku_code"],
            location_id=loc_id,
            location_code=loc["location_code"],
            target_week=target_week,
            recoverable_quantity=recoverable_qty if is_feasible else 0,
            quantity_still_at_risk=max(0, deficit - recoverable_qty) if is_feasible else deficit,
            additional_procurement_cost=total_procurement_cost,
            transportation_cost=0.0,
            production_cost=0.0,
            total_cost=total_cost,
            expected_arrival_date=arr_date.isoformat()[:10],
            expected_arrival_week=arr_week,
            recovery_time_days=lead_time_days,
            service_level_impact=service_gain if is_feasible else 0.0,
            roi_ratio=roi if is_feasible else 0.0,
            is_feasible=is_feasible,
            infeasibility_reasons=infeasibility_reasons,
            source_reference_id=supp_code,
            explanation=explanation,
            details={"supplier_id": supp_id, "moq": moq, "available_capacity": available_cap},
        )

    def _eval_expedited_shipment(
        self,
        shortage_id: str,
        sku: Dict[str, Any],
        loc: Dict[str, Any],
        target_week: str,
        req_date: datetime,
        now: datetime,
        deficit: int,
    ) -> Optional[MitigationCandidate]:
        """Option 3: Expedited Shipment on open PO line."""
        sku_id = sku["id"]
        loc_id = loc["id"]
        pol_candidates = self.open_po_lines.get((sku_id, loc_id), [])

        # Find an open PO line scheduled after shortage or in transit
        suitable_pol = None
        for pol in pol_candidates:
            open_bal = int(pol.get("ordered_qty", 0)) - int(pol.get("received_qty", 0))
            if open_bal > 0:
                suitable_pol = pol
                break

        if not suitable_pol:
            return None

        infeasibility_reasons = []
        open_bal = int(suitable_pol.get("ordered_qty", 0)) - int(suitable_pol.get("received_qty", 0))
        prom_date_str = suitable_pol.get("promised_delivery_date")
        prom_date = datetime.fromisoformat(str(prom_date_str).replace("Z", "+00:00")) if prom_date_str else req_date

        # Standard transit days
        std_days = max(1, (prom_date - now).days)
        exp_days = max(self.config.min_expedited_days, int(std_days * self.config.expedited_lead_time_factor))
        exp_date = now + timedelta(days=exp_days)
        exp_week = parse_week_bucket(exp_date)

        if exp_date > req_date and exp_week > target_week:
            infeasibility_reasons.append(
                f"Even with air expedite ({exp_days} days), arrival in {exp_week} misses required period {target_week}."
            )

        recoverable_qty = min(deficit, open_bal)
        is_feasible = (len(infeasibility_reasons) == 0 and recoverable_qty > 0)

        air_premium = round(recoverable_qty * self.config.air_freight_premium_per_unit, 2)
        service_gain = round((recoverable_qty / deficit) * 100.0, 2) if deficit > 0 else 100.0
        revenue_protected = recoverable_qty * float(sku.get("unit_price", 100.0))
        roi = round(revenue_protected / max(air_premium, 1.0), 4)

        explanation = (
            f"Expedite PO line {suitable_pol.get('id', 'N/A')} via air freight: compresses lead time from "
            f"{std_days}d to {exp_days}d. Delivers {recoverable_qty} units in {exp_week}."
        )
        if not is_feasible:
            explanation = f"Infeasible: {'; '.join(infeasibility_reasons)}"

        return MitigationCandidate(
            shortage_id=shortage_id,
            action_type=MitigationActionType.EXPEDITED_SHIPMENT,
            sku_id=sku_id,
            sku_code=sku["sku_code"],
            location_id=loc_id,
            location_code=loc["location_code"],
            target_week=target_week,
            recoverable_quantity=recoverable_qty if is_feasible else 0,
            quantity_still_at_risk=max(0, deficit - recoverable_qty) if is_feasible else deficit,
            additional_procurement_cost=0.0,
            transportation_cost=air_premium,
            production_cost=0.0,
            total_cost=air_premium,
            expected_arrival_date=exp_date.isoformat()[:10],
            expected_arrival_week=exp_week,
            recovery_time_days=exp_days,
            service_level_impact=service_gain if is_feasible else 0.0,
            roi_ratio=roi if is_feasible else 0.0,
            is_feasible=is_feasible,
            infeasibility_reasons=infeasibility_reasons,
            source_reference_id=str(suitable_pol.get("po_id")),
            explanation=explanation,
            details={"po_line_id": suitable_pol.get("id"), "freight_premium": air_premium},
        )

    def _eval_inventory_transfer(
        self,
        shortage_id: str,
        sku: Dict[str, Any],
        loc: Dict[str, Any],
        target_week: str,
        req_date: datetime,
        now: datetime,
        deficit: int,
    ) -> List[MitigationCandidate]:
        """Option 4: Inter-Facility Transfer preserving source safety stock."""
        sku_id = sku["id"]
        dest_loc_id = loc["id"]
        candidates = []

        # Search other locations for surplus
        for other_loc_id, other_loc in self.locations.items():
            if other_loc_id == dest_loc_id:
                continue

            inv = self.inventories.get((sku_id, other_loc_id))
            if not inv:
                continue

            on_hand = int(inv.get("on_hand_qty", 0))
            allocated = int(inv.get("allocated_qty", 0))
            ss = int(inv.get("safety_stock_qty", 0))

            # Feasibility Rule: Preserve source safety stock
            surplus = max(0, on_hand - allocated - ss)
            if surplus <= 0:
                continue

            infeasibility_reasons = []

            # Transit duration & freight cost from lane or geographic matrix
            lane = self.lanes.get((other_loc_id, dest_loc_id))
            if lane:
                transit_days = int(lane.get("transit_days", 3))
                cost_per_unit = float(lane.get("cost_per_unit", self.config.default_transfer_cost_per_unit))
            else:
                src_country = other_loc.get("country", "USA")
                dest_country = loc.get("country", "USA")
                if src_country == dest_country:
                    transit_days = 2
                    cost_per_unit = self.config.default_transfer_cost_per_unit
                else:
                    transit_days = 4
                    cost_per_unit = round(self.config.default_transfer_cost_per_unit * 1.8, 2)

            arr_date = now + timedelta(days=transit_days)
            arr_week = parse_week_bucket(arr_date)

            if arr_date > req_date and arr_week > target_week:
                infeasibility_reasons.append(
                    f"Transfer transit time ({transit_days}d) arrives in {arr_week}, after required period {target_week}."
                )

            transfer_qty = min(deficit, surplus)
            is_feasible = (len(infeasibility_reasons) == 0 and transfer_qty > 0)

            freight_cost = round(transfer_qty * cost_per_unit, 2)
            service_gain = round((transfer_qty / deficit) * 100.0, 2) if deficit > 0 else 100.0
            revenue_protected = transfer_qty * float(sku.get("unit_price", 100.0))
            roi = round(revenue_protected / max(freight_cost, 1.0), 4)

            explanation = (
                f"Transfer {transfer_qty} units from {other_loc.get('location_code')} (Surplus: {surplus}, SS preserved: {ss}). "
                f"Transit: {transit_days}d via road freight."
            )
            if not is_feasible:
                explanation = f"Infeasible: {'; '.join(infeasibility_reasons)}"

            candidates.append(
                MitigationCandidate(
                    shortage_id=shortage_id,
                    action_type=MitigationActionType.INVENTORY_TRANSFER,
                    sku_id=sku_id,
                    sku_code=sku["sku_code"],
                    location_id=dest_loc_id,
                    location_code=loc["location_code"],
                    target_week=target_week,
                    recoverable_quantity=transfer_qty if is_feasible else 0,
                    quantity_still_at_risk=max(0, deficit - transfer_qty) if is_feasible else deficit,
                    additional_procurement_cost=0.0,
                    transportation_cost=freight_cost,
                    production_cost=0.0,
                    total_cost=freight_cost,
                    expected_arrival_date=arr_date.isoformat()[:10],
                    expected_arrival_week=arr_week,
                    recovery_time_days=transit_days,
                    service_level_impact=service_gain if is_feasible else 0.0,
                    roi_ratio=roi if is_feasible else 0.0,
                    is_feasible=is_feasible,
                    infeasibility_reasons=infeasibility_reasons,
                    source_reference_id=other_loc.get("location_code"),
                    explanation=explanation,
                    details={"source_location_id": other_loc_id, "source_surplus": surplus},
                )
            )

        return candidates

    def _eval_production_increase(
        self,
        shortage_id: str,
        sku: Dict[str, Any],
        loc: Dict[str, Any],
        target_week: str,
        req_date: datetime,
        now: datetime,
        deficit: int,
    ) -> Optional[MitigationCandidate]:
        """Option 5: Production Increase at manufacturing facility."""
        sku_type = sku.get("sku_type", "").upper()
        if sku_type not in (SKUType.FINISHED_GOOD.value, SKUType.SUBASSEMBLY.value):
            return None

        # Look for manufacturing plants
        plant = None
        if loc.get("location_type") == LocationType.PLANT.value:
            plant = loc
        else:
            for l in self.locations.values():
                if l.get("location_type") == LocationType.PLANT.value:
                    plant = l
                    break

        if not plant:
            return None

        infeasibility_reasons = []
        plant_cap = int(plant.get("capacity_units", 10000))

        # Check plant capacity
        if plant_cap <= 0:
            infeasibility_reasons.append(f"Plant {plant.get('location_code')} has 0 manufacturing throughput.")

        # Check BOM and component availability
        boms = self.boms_by_parent.get(sku["id"], [])
        max_from_bom = deficit
        if boms:
            bom = boms[0]
            components = self.bom_components_by_bom.get(bom["id"], [])
            for c in components:
                c_sku_id = c["component_sku_id"]
                c_inv = self.inventories.get((c_sku_id, plant["id"]))
                c_on_hand = int(c_inv.get("on_hand_qty", 0)) if c_inv else 0
                c_ss = int(c_inv.get("safety_stock_qty", 0)) if c_inv else 0
                c_surplus = max(0, c_on_hand - c_ss)
                qty_per = float(c.get("quantity_per_parent", 1.0))
                scrap = float(c.get("scrap_percentage", 0.0))

                eff_qty_per = qty_per / max(0.01, (1.0 - scrap))
                max_parent = int(c_surplus / eff_qty_per) if eff_qty_per > 0 else 0
                max_from_bom = min(max_from_bom, max_parent)
                if max_parent <= 0:
                    c_sku = self.skus.get(c_sku_id, {})
                    infeasibility_reasons.append(
                        f"Critical BOM component {c_sku.get('sku_code', 'N/A')} has zero surplus inventory at plant."
                    )
        else:
            infeasibility_reasons.append("No active Bill of Materials found for this parent SKU.")

        # Production lead time
        prod_days = 4
        arr_date = now + timedelta(days=prod_days)
        arr_week = parse_week_bucket(arr_date)

        if arr_date > req_date and arr_week > target_week:
            infeasibility_reasons.append(
                f"Production lead time ({prod_days}d) finishes in {arr_week}, after required shortage week {target_week}."
            )

        recoverable_qty = min(deficit, plant_cap, max_from_bom)
        is_feasible = (len(infeasibility_reasons) == 0 and recoverable_qty > 0)

        # Cost: Setup + overtime production labor
        prod_cost = round(self.config.production_setup_cost + (recoverable_qty * self.config.production_overtime_cost_per_unit), 2)
        service_gain = round((recoverable_qty / deficit) * 100.0, 2) if deficit > 0 else 100.0
        revenue_protected = recoverable_qty * float(sku.get("unit_price", 100.0))
        roi = round(revenue_protected / max(prod_cost, 1.0), 4)

        explanation = (
            f"Increase production batch by {recoverable_qty} units at {plant.get('location_code')} "
            f"(BOM components verified, 4-day cycle time). Setup: ${self.config.production_setup_cost}."
        )
        if not is_feasible:
            explanation = f"Infeasible: {'; '.join(infeasibility_reasons)}"

        return MitigationCandidate(
            shortage_id=shortage_id,
            action_type=MitigationActionType.PRODUCTION_INCREASE,
            sku_id=sku["id"],
            sku_code=sku["sku_code"],
            location_id=loc["id"],
            location_code=loc["location_code"],
            target_week=target_week,
            recoverable_quantity=recoverable_qty if is_feasible else 0,
            quantity_still_at_risk=max(0, deficit - recoverable_qty) if is_feasible else deficit,
            additional_procurement_cost=0.0,
            transportation_cost=0.0,
            production_cost=prod_cost,
            total_cost=prod_cost,
            expected_arrival_date=arr_date.isoformat()[:10],
            expected_arrival_week=arr_week,
            recovery_time_days=prod_days,
            service_level_impact=service_gain if is_feasible else 0.0,
            roi_ratio=roi if is_feasible else 0.0,
            is_feasible=is_feasible,
            infeasibility_reasons=infeasibility_reasons,
            source_reference_id=plant.get("location_code"),
            explanation=explanation,
            details={"plant_id": plant["id"], "max_from_bom": max_from_bom},
        )

    def _eval_substitute_sku(
        self,
        shortage_id: str,
        sku: Dict[str, Any],
        loc: Dict[str, Any],
        target_week: str,
        req_date: datetime,
        now: datetime,
        deficit: int,
    ) -> List[MitigationCandidate]:
        """Option 6: Approved Substitute SKU."""
        sku_id = sku["id"]
        loc_id = loc["id"]
        subs = self.substitutes.get(sku_id, [])
        candidates = []

        now_str = now.isoformat()[:10]

        for sub in subs:
            sub_sku_id = sub["substitute_sku_id"]
            sub_sku = self.skus.get(sub_sku_id, {})
            sub_code = sub_sku.get("sku_code", "SUB-UNKNOWN")

            infeasibility_reasons = []

            # 1. Substitute must be approved (valid dates)
            eff_from = sub.get("effective_from")
            eff_to = sub.get("effective_to")
            if eff_from and str(eff_from)[:10] > now_str:
                infeasibility_reasons.append(f"Substitute approval effective from {eff_from} is not yet active.")
            if eff_to and str(eff_to)[:10] < now_str:
                infeasibility_reasons.append(f"Substitute approval for {sub_code} expired on {eff_to} (unapproved).")

            # 2. Check substitute inventory surplus at location
            sub_inv = self.inventories.get((sub_sku_id, loc_id))
            sub_on_hand = int(sub_inv.get("on_hand_qty", 0)) if sub_inv else 0
            sub_alloc = int(sub_inv.get("allocated_qty", 0)) if sub_inv else 0
            sub_ss = int(sub_inv.get("safety_stock_qty", 0)) if sub_inv else 0
            sub_surplus = max(0, sub_on_hand - sub_alloc - sub_ss)

            conversion = float(sub.get("conversion_factor", 1.0))
            if conversion <= 0:
                infeasibility_reasons.append(f"Invalid conversion factor {conversion}.")
                conversion = 1.0

            avail_equiv = int(sub_surplus / conversion)
            if avail_equiv <= 0:
                infeasibility_reasons.append(
                    f"Substitute SKU {sub_code} has zero surplus inventory (on-hand: {sub_on_hand}, SS: {sub_ss})."
                )

            recoverable_qty = min(deficit, avail_equiv)
            is_feasible = (len(infeasibility_reasons) == 0 and recoverable_qty > 0)

            # Cost differential (if substitute is more expensive)
            orig_cost = float(sku.get("unit_cost", 10.0))
            sub_cost = float(sub_sku.get("unit_cost", orig_cost))
            cost_diff = max(0.0, (sub_cost * conversion) - orig_cost)
            total_sub_cost = round(recoverable_qty * cost_diff, 2)

            service_gain = round((recoverable_qty / deficit) * 100.0, 2) if deficit > 0 else 100.0
            revenue_protected = recoverable_qty * float(sku.get("unit_price", 100.0))
            roi = round(revenue_protected / max(total_sub_cost, 1.0), 4)

            explanation = (
                f"Substitute with approved SKU {sub_code} (1:{conversion:.2f} ratio). "
                f"Consumes {int(recoverable_qty * conversion)} units of surplus stock immediately (0-day lead time)."
            )
            if not is_feasible:
                explanation = f"Infeasible: {'; '.join(infeasibility_reasons)}"

            candidates.append(
                MitigationCandidate(
                    shortage_id=shortage_id,
                    action_type=MitigationActionType.APPROVED_SUBSTITUTE_SKU,
                    sku_id=sku_id,
                    sku_code=sku["sku_code"],
                    location_id=loc_id,
                    location_code=loc["location_code"],
                    target_week=target_week,
                    recoverable_quantity=recoverable_qty if is_feasible else 0,
                    quantity_still_at_risk=max(0, deficit - recoverable_qty) if is_feasible else deficit,
                    additional_procurement_cost=total_sub_cost,
                    transportation_cost=0.0,
                    production_cost=0.0,
                    total_cost=total_sub_cost,
                    expected_arrival_date=now.isoformat()[:10],
                    expected_arrival_week=target_week,
                    recovery_time_days=0,
                    service_level_impact=service_gain if is_feasible else 0.0,
                    roi_ratio=roi if is_feasible else 0.0,
                    is_feasible=is_feasible,
                    infeasibility_reasons=infeasibility_reasons,
                    source_reference_id=sub_code,
                    explanation=explanation,
                    details={"substitute_sku_id": sub_sku_id, "conversion_factor": conversion},
                )
            )

        return candidates

"""SupplyChain IQ - Root Cause Analysis Engine for Shortages."""

from typing import Any, Dict, List, Optional, Tuple

from backend.app.planning.models import ShortageRootCause


class RootCauseAnalyzer:
    """Diagnoses root cause category and generates human-readable explanations

    for supply chain inventory deficits across the 8 standard categories:
    - Demand spike
    - Insufficient opening inventory
    - Supplier delay
    - Supplier capacity shortage
    - Production constraint
    - Transportation delay
    - Missing lead time
    - Invalid substitute
    """

    def __init__(self, demand_spike_multiplier: float = 1.5):
        self.demand_spike_multiplier = demand_spike_multiplier

    def diagnose(
        self,
        sku_code: str,
        location_code: str,
        week_bucket: str,
        week_index: int,
        demand_qty: int,
        avg_demand: float,
        opening_on_hand: int,
        safety_stock: int,
        missing_lead_time: bool = False,
        invalid_substitute: bool = False,
        delayed_shipments: Optional[List[Dict[str, Any]]] = None,
        delayed_pos: Optional[List[Dict[str, Any]]] = None,
        supplier_capacity_exceeded: Optional[Dict[str, Any]] = None,
        production_constrained: Optional[Dict[str, Any]] = None,
    ) -> Tuple[ShortageRootCause, str]:
        """Evaluate deterministic diagnostic rules in priority order.

        Returns:
            (root_cause_enum, human_readable_explanation)
        """
        delayed_shipments = delayed_shipments or []
        delayed_pos = delayed_pos or []

        # 1. Missing Lead Time master data anomaly / gap
        if missing_lead_time:
            return (
                ShortageRootCause.MISSING_LEAD_TIME,
                f"Supplier catalog lead time for SKU {sku_code} is not configured or zero; replenishment orders could not be phased in advance.",
            )

        # 2. Invalid or expired substitute SKU
        if invalid_substitute:
            return (
                ShortageRootCause.INVALID_SUBSTITUTE,
                f"Candidate substitute SKU for {sku_code} is expired or unapproved, preventing automated component substitution.",
            )

        # 3. Supplier Capacity Ceiling Exceeded
        if supplier_capacity_exceeded:
            cap = supplier_capacity_exceeded.get("max_capacity_units", 0)
            committed = supplier_capacity_exceeded.get("committed_units", 0)
            return (
                ShortageRootCause.SUPPLIER_CAPACITY_SHORTAGE,
                f"Supplier capacity ceiling ({cap} units) was exceeded by committed inbound volume ({committed} units), limiting scheduled purchase receipts.",
            )

        # 4. Production Work Center Capacity Constraint
        if production_constrained:
            cap = production_constrained.get("capacity_units", 0)
            planned = production_constrained.get("planned_units", 0)
            return (
                ShortageRootCause.PRODUCTION_CONSTRAINT,
                f"Manufacturing plant capacity ceiling of {cap} units restricted planned production output ({planned} units requested).",
            )

        # 5. Transportation / Logistics delay
        if delayed_shipments:
            s = delayed_shipments[0]
            track_num = s.get("tracking_number", "UNKNOWN")
            orig_date = s.get("promised_date", "scheduled date")
            rev_date = s.get("revised_date", "revised date")
            return (
                ShortageRootCause.TRANSPORTATION_DELAY,
                f"In-transit shipment {track_num} experienced transit/customs delay (shifted from {orig_date} to {rev_date}), missing arrival in {week_bucket}.",
            )

        # 6. Supplier PO Delay
        if delayed_pos:
            po = delayed_pos[0]
            po_num = po.get("po_number", "UNKNOWN")
            return (
                ShortageRootCause.SUPPLIER_DELAY,
                f"Inbound purchase order {po_num} promised delivery date falls after replenishment requirement date for period {week_bucket}.",
            )

        # 7. Demand Spike
        if avg_demand > 0 and demand_qty >= (avg_demand * self.demand_spike_multiplier):
            ratio = demand_qty / avg_demand
            return (
                ShortageRootCause.DEMAND_SPIKE,
                f"Forecast demand of {demand_qty} units in {week_bucket} is {ratio:.1f}x higher than historical average demand ({avg_demand:.1f} units).",
            )

        # 8. Insufficient Opening Inventory
        if week_index <= 2 and opening_on_hand < safety_stock:
            return (
                ShortageRootCause.INSUFFICIENT_OPENING_INVENTORY,
                f"Opening on-hand stock ({opening_on_hand} units) at beginning of horizon was insufficient to cover target safety stock buffer ({safety_stock} units).",
            )

        # Fallback diagnostics based on horizon progression
        if avg_demand > 0 and demand_qty > avg_demand * 1.15:
            ratio = demand_qty / avg_demand
            return (
                ShortageRootCause.DEMAND_SPIKE,
                f"Surge demand of {demand_qty} units in {week_bucket} exceeded average demand ({avg_demand:.1f} units).",
            )

        if opening_on_hand <= 0 and week_index <= 3:
            return (
                ShortageRootCause.INSUFFICIENT_OPENING_INVENTORY,
                f"Zero or negligible starting inventory at facility {location_code} left zero buffer before replenishment.",
            )

        # Default SCM diagnosis: Supplier lead time replenishment gap
        return (
            ShortageRootCause.SUPPLIER_DELAY,
            f"Replenishment lead time for {sku_code} at {location_code} exceeded the horizon window before demand consumption in {week_bucket}.",
        )

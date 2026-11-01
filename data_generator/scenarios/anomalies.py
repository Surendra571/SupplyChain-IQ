"""SupplyChain IQ - Separate Labeled Anomaly Injection & Ground Truth Generation."""

import copy
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Tuple


class AnomalyInjector:
    """Injects five deliberate, domain-specific supply chain data anomalies into a baseline dataset.
    Generates an isolated ground_truth catalog mapping each anomaly to its target entity.
    """

    def __init__(self, baseline_dataset: Dict[str, List[Dict[str, Any]]]):
        # Perform deep copy to ensure baseline dataset is never mutated
        self.dataset = copy.deepcopy(baseline_dataset)
        self.ground_truth: List[Dict[str, Any]] = []

    def inject_all(self) -> Tuple[Dict[str, List[Dict[str, Any]]], List[Dict[str, Any]]]:
        """Inject all 5 distinct anomaly scenarios and return mutated dataset + ground_truth labels."""
        self._inject_1_inbound_inventory_counted_twice()
        self._inject_2_substitute_sku_not_approved()
        self._inject_3_supplier_capacity_exceeded()
        self._inject_4_shortage_without_lead_time()
        self._inject_5_unit_of_measure_mismatch()

        return self.dataset, self.ground_truth

    # -------------------------------------------------------------------------
    # Scenario 1: Inbound Inventory Counted Twice
    # -------------------------------------------------------------------------
    def _inject_1_inbound_inventory_counted_twice(self):
        # Target an inventory record with positive balance
        inv = self.dataset["inventories"][0]
        original_qty = inv["on_hand_qty"]
        duplicate_shipment_qty = 500
        anomalous_qty = original_qty + duplicate_shipment_qty

        inv["on_hand_qty"] = anomalous_qty

        # Inject duplicate transaction
        dup_tx_bid = "TXN-ANOM-DUP-01"
        self.dataset["inventory_transactions"].append({
            "id": "00000000-0000-0000-0000-000000000001",
            "business_id": dup_tx_bid,
            "sku_id": inv["sku_id"],
            "location_id": inv["location_id"],
            "transaction_type": "RECEIPT",
            "quantity": duplicate_shipment_qty,
            "balance_after": anomalous_qty,
            "reference_id": "PO-DUPLICATE-POSTING",
            "notes": "ANOMALY: Inbound shipment counted twice in physical inventory ledger",
            "created_at": inv["created_at"],
        })

        self.ground_truth.append({
            "anomaly_id": "ANOM-001",
            "scenario_name": "Inbound inventory counted twice",
            "anomaly_type": "INBOUND_INVENTORY_COUNTED_TWICE",
            "target_entity": "inventories",
            "target_business_id": inv["business_id"],
            "injected_field": "on_hand_qty",
            "baseline_value": str(original_qty),
            "anomalous_value": str(anomalous_qty),
            "severity": "CRITICAL",
            "description": f"Shipment receipt of {duplicate_shipment_qty} units was posted twice, creating phantom stock and masking shortages.",
        })

    # -------------------------------------------------------------------------
    # Scenario 2: Substitute SKU Not Approved / Expired
    # -------------------------------------------------------------------------
    def _inject_2_substitute_sku_not_approved(self):
        # Target first substitute SKU relationship or create one
        if self.dataset["substitute_skus"]:
            subst = self.dataset["substitute_skus"][0]
            orig_effective_to = subst["effective_to"]
            # Set historical approval window that has now expired
            subst["effective_from"] = "2025-01-01T00:00:00+00:00"
            expired_date = "2025-12-31T23:59:59+00:00"
            subst["effective_to"] = expired_date

            self.ground_truth.append({
                "anomaly_id": "ANOM-002",
                "scenario_name": "Substitute SKU not approved",
                "anomaly_type": "SUBSTITUTE_SKU_NOT_APPROVED",
                "target_entity": "substitute_skus",
                "target_business_id": subst["business_id"],
                "injected_field": "effective_to",
                "baseline_value": str(orig_effective_to),
                "anomalous_value": expired_date,
                "severity": "HIGH",
                "description": "Component substitution relationship has expired effective_to date, rendering alternate sourcing unapproved.",
            })

    # -------------------------------------------------------------------------
    # Scenario 3: Supplier Capacity Exceeded
    # -------------------------------------------------------------------------
    def _inject_3_supplier_capacity_exceeded(self):
        # Target a supplier capacity record and inflate assigned PO commitments beyond max
        cap = self.dataset["supplier_capacities"][0]
        max_cap = cap["max_capacity_units"]
        surge_cap = cap["surge_capacity_units"]
        orig_committed = cap["committed_units"]
        # Overcommit by 150% of allowable capacity
        overcommitted_qty = int((max_cap + surge_cap) * 1.5)
        cap["committed_units"] = overcommitted_qty

        self.ground_truth.append({
            "anomaly_id": "ANOM-003",
            "scenario_name": "Supplier capacity exceeded",
            "anomaly_type": "SUPPLIER_CAPACITY_EXCEEDED",
            "target_entity": "supplier_capacities",
            "target_business_id": cap["business_id"],
            "injected_field": "committed_units",
            "baseline_value": str(orig_committed),
            "anomalous_value": str(overcommitted_qty),
            "severity": "CRITICAL",
            "description": f"Open PO line commitments ({overcommitted_qty} units) exceed maximum supplier capacity ({max_cap} units + {surge_cap} surge).",
        })

    # -------------------------------------------------------------------------
    # Scenario 4: Shortage Calculated Without Lead Time
    # -------------------------------------------------------------------------
    def _inject_4_shortage_without_lead_time(self):
        # Target a PO line and set promised delivery date prior to order date
        line = self.dataset["purchase_order_lines"][0]
        orig_delivery = line["promised_delivery_date"]
        # Make promised delivery in the past relative to snapshot
        past_date = "2025-12-01T00:00:00+00:00"
        line["promised_delivery_date"] = past_date

        self.ground_truth.append({
            "anomaly_id": "ANOM-004",
            "scenario_name": "Shortage calculated without lead time",
            "anomaly_type": "SHORTAGE_CALCULATED_WITHOUT_LEAD_TIME",
            "target_entity": "purchase_order_lines",
            "target_business_id": line["business_id"],
            "injected_field": "promised_delivery_date",
            "baseline_value": str(orig_delivery),
            "anomalous_value": past_date,
            "severity": "HIGH",
            "description": "Purchase order promised delivery date is in the past, violating minimum procurement lead time constraints.",
        })

    # -------------------------------------------------------------------------
    # Scenario 5: Unit of Measure Mismatch
    # -------------------------------------------------------------------------
    def _inject_5_unit_of_measure_mismatch(self):
        # Target a PO line and mutate its unit cost or ordered quantity by 50x (e.g. BOX vs EA)
        line = self.dataset["purchase_order_lines"][-1]
        orig_cost = line["unit_cost"]
        # 50x factor representing pack size mismatch
        mismatched_cost = orig_cost * 50.0
        line["unit_cost"] = mismatched_cost

        self.ground_truth.append({
            "anomaly_id": "ANOM-005",
            "scenario_name": "Unit of measure mismatch",
            "anomaly_type": "UNIT_OF_MEASURE_MISMATCH",
            "target_entity": "purchase_order_lines",
            "target_business_id": line["business_id"],
            "injected_field": "unit_cost",
            "baseline_value": str(orig_cost),
            "anomalous_value": str(mismatched_cost),
            "severity": "CRITICAL",
            "description": f"Unit cost inflated by 50x (from {orig_cost} to {mismatched_cost}) due to BOX vs EA unit of measure conversion failure.",
        })


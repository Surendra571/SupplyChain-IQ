"""SupplyChain IQ - Core Deterministic Synthetic Data Generator."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import math
import random
from typing import Any, Dict, List, Tuple
import uuid

import numpy as np

from backend.app.generator.config import GeneratorConfig, ScaleConfig
from backend.app.models.enums import (
    InventoryTransactionType,
    LocationType,
    ProductionPlanStatus,
    PurchaseOrderStatus,
    ShipmentStatus,
    SKUType,
    SupplierTier,
    TransportMode,
)

UUID_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")  # RFC 4122 DNS namespace


def make_deterministic_uuid(entity_name: str, business_id: str) -> uuid.UUID:
    """Generate a deterministic UUIDv5 from entity name and business ID."""
    return uuid.uuid5(UUID_NAMESPACE, f"supplychain-iq:{entity_name}:{business_id}")


class SyntheticDataGenerator:
    """Generates complete, valid baseline supply chain planning datasets deterministically."""

    def __init__(self, config: GeneratorConfig):
        self.config = config
        self.scale: ScaleConfig = config.current_scale
        self.seed = config.seed

        # Initialize deterministic pseudo-random generators
        self.rng = random.Random(self.seed)
        self.np_rng = np.random.default_rng(self.seed)

        # Baseline snapshot timeline reference: 2026-01-05 (Monday of Week 1, 2026)
        self.base_date = datetime(2026, 1, 5, 0, 0, 0, tzinfo=timezone.utc)

        # Generated entity storage
        self.skus: List[Dict[str, Any]] = []
        self.locations: List[Dict[str, Any]] = []
        self.suppliers: List[Dict[str, Any]] = []
        self.supplier_skus: List[Dict[str, Any]] = []
        self.boms: List[Dict[str, Any]] = []
        self.bom_components: List[Dict[str, Any]] = []
        self.substitute_skus: List[Dict[str, Any]] = []
        self.forecast_demands: List[Dict[str, Any]] = []
        self.inventories: List[Dict[str, Any]] = []
        self.inventory_transactions: List[Dict[str, Any]] = []
        self.supplier_capacities: List[Dict[str, Any]] = []
        self.lead_times: List[Dict[str, Any]] = []
        self.production_plans: List[Dict[str, Any]] = []
        self.purchase_orders: List[Dict[str, Any]] = []
        self.purchase_order_lines: List[Dict[str, Any]] = []
        self.shipments: List[Dict[str, Any]] = []

    def get_week_str(self, week_num: int) -> str:
        """Return formatted week string, e.g. 2026W01."""
        return f"2026W{week_num:02d}"

    def get_week_date(self, week_num: int) -> datetime:
        """Return date corresponding to the Monday of given week."""
        return self.base_date + timedelta(weeks=(week_num - 1))

    def generate_all(self) -> Dict[str, List[Dict[str, Any]]]:
        """Execute generation in strict order (1 to 13)."""
        self._gen_1_skus()
        self._gen_2_locations()
        self._gen_3_suppliers()
        self._gen_4_supplier_skus()
        self._gen_5_boms_and_substitutes()
        self._gen_6_forecast_demand()
        self._gen_7_opening_inventory()
        self._gen_8_supplier_capacity()
        self._gen_9_lead_times()
        self._gen_10_production_capacity()
        self._gen_11_purchase_orders()
        self._gen_12_purchase_order_lines()
        self._gen_13_shipments()

        return self.get_dataset()

    def get_dataset(self) -> Dict[str, List[Dict[str, Any]]]:
        """Return dictionary of all generated entity collections."""
        return {
            "skus": self.skus,
            "locations": self.locations,
            "suppliers": self.suppliers,
            "supplier_skus": self.supplier_skus,
            "boms": self.boms,
            "bom_components": self.bom_components,
            "substitute_skus": self.substitute_skus,
            "forecast_demands": self.forecast_demands,
            "inventories": self.inventories,
            "inventory_transactions": self.inventory_transactions,
            "supplier_capacities": self.supplier_capacities,
            "lead_times": self.lead_times,
            "production_plans": self.production_plans,
            "purchase_orders": self.purchase_orders,
            "purchase_order_lines": self.purchase_order_lines,
            "shipments": self.shipments,
        }

    # -------------------------------------------------------------------------
    # 1. SKU Master
    # -------------------------------------------------------------------------
    def _gen_1_skus(self):
        n_skus = self.scale.skus
        # ~20% Finished Goods, ~30% Subassemblies, ~50% Raw Materials
        n_fg = max(1, int(n_skus * 0.20))
        n_sub = max(1, int(n_skus * 0.30))
        n_rm = n_skus - n_fg - n_sub

        sku_types = (
            [SKUType.FINISHED_GOOD] * n_fg
            + [SKUType.SUBASSEMBLY] * n_sub
            + [SKUType.RAW_MATERIAL] * n_rm
        )

        categories = self.config.categories
        uoms = self.config.units_of_measure

        for i, stype in enumerate(sku_types, start=1):
            bid = f"SKU-{i:06d}"
            sku_id = make_deterministic_uuid("skus", bid)

            if stype == SKUType.FINISHED_GOOD:
                code_prefix = "FG"
                cost = Decimal(f"{self.rng.uniform(80.0, 450.0):.4f}")
                price = Decimal(f"{float(cost) * self.rng.uniform(1.4, 2.0):.4f}")
                uom = "EA"
                cat = "Electronics" if i % 2 == 0 else "Mechanical"
            elif stype == SKUType.SUBASSEMBLY:
                code_prefix = "SUB"
                cost = Decimal(f"{self.rng.uniform(25.0, 120.0):.4f}")
                price = Decimal(f"{float(cost) * self.rng.uniform(1.3, 1.7):.4f}")
                uom = "EA"
                cat = "Subassemblies"
            else:
                code_prefix = "RM"
                cost = Decimal(f"{self.rng.uniform(1.5, 45.0):.4f}")
                price = Decimal(f"{float(cost) * self.rng.uniform(1.2, 1.5):.4f}")
                uom = self.rng.choice(uoms)
                cat = self.rng.choice(["Raw Materials", "Packaging", "Electronics"])

            weight = Decimal(f"{self.rng.uniform(0.05, 12.5):.3f}")

            self.skus.append({
                "id": str(sku_id),
                "business_id": bid,
                "sku_code": f"SKU-{code_prefix}-{i:05d}",
                "name": f"{cat} Item {i:04d} ({stype.value})",
                "category": cat,
                "sku_type": stype.value,
                "unit_of_measure": uom,
                "unit_cost": float(cost),
                "unit_price": float(price),
                "weight_kg": float(weight),
                "is_active": True,
                "created_at": self.base_date.isoformat(),
                "updated_at": self.base_date.isoformat(),
            })

    # -------------------------------------------------------------------------
    # 2. Location Master
    # -------------------------------------------------------------------------
    def _gen_2_locations(self):
        n_locs = self.scale.locations
        countries = ["USA", "CAN", "MEX", "DEU", "JPN", "GBR"]
        types = [LocationType.PLANT, LocationType.DC, LocationType.WAREHOUSE]

        for i in range(1, n_locs + 1):
            bid = f"LOC-{i:06d}"
            loc_id = make_deterministic_uuid("locations", bid)
            ltype = types[(i - 1) % len(types)]
            country = countries[(i - 1) % len(countries)]
            capacity = 100000 + (i * 25000)

            self.locations.append({
                "id": str(loc_id),
                "business_id": bid,
                "location_code": f"LOC-{ltype.value[:2]}-{i:04d}",
                "name": f"{country} {ltype.value} Facility {i}",
                "location_type": ltype.value,
                "capacity_units": capacity,
                "country": country,
                "is_active": True,
                "created_at": self.base_date.isoformat(),
                "updated_at": self.base_date.isoformat(),
            })

    # -------------------------------------------------------------------------
    # 3. Supplier Master
    # -------------------------------------------------------------------------
    def _gen_3_suppliers(self):
        n_sups = self.scale.suppliers
        tiers = [SupplierTier.STRATEGIC, SupplierTier.TIER_1, SupplierTier.TIER_2, SupplierTier.TIER_3]
        countries = ["USA", "TWN", "JPN", "DEU", "KOR", "VNM", "MEX"]
        terms = ["NET30", "NET45", "NET60"]

        for i in range(1, n_sups + 1):
            bid = f"SUP-{i:06d}"
            sup_id = make_deterministic_uuid("suppliers", bid)
            tier = tiers[(i - 1) % len(tiers)]
            country = countries[(i - 1) % len(countries)]
            otd = Decimal(f"{self.rng.uniform(0.8800, 0.9950):.4f}")

            self.suppliers.append({
                "id": str(sup_id),
                "business_id": bid,
                "supplier_code": f"SUP-VEND-{i:04d}",
                "name": f"Supplier Partner {i:04d} Corp",
                "tier": tier.value,
                "country": country,
                "payment_terms": terms[i % len(terms)],
                "on_time_delivery_rate": float(otd),
                "is_active": True,
                "created_at": self.base_date.isoformat(),
                "updated_at": self.base_date.isoformat(),
            })

    # -------------------------------------------------------------------------
    # 4. Supplier-SKU Relationships
    # -------------------------------------------------------------------------
    def _gen_4_supplier_skus(self):
        # Assign suppliers to all RAW_MATERIAL and SUBASSEMBLY SKUs
        purchasable_skus = [s for s in self.skus if s["sku_type"] in [SKUType.RAW_MATERIAL.value, SKUType.SUBASSEMBLY.value]]
        if not purchasable_skus:
            purchasable_skus = self.skus

        ssku_count = 0
        for sku in purchasable_skus:
            # 1 to 3 suppliers per purchasable SKU
            n_vendors = min(len(self.suppliers), self.rng.randint(1, 3))
            assigned_sups = self.rng.sample(self.suppliers, n_vendors)

            for rank, sup in enumerate(assigned_sups):
                ssku_count += 1
                bid = f"SUPSK-{ssku_count:06d}"
                ssku_id = make_deterministic_uuid("supplier_skus", bid)
                is_pref = (rank == 0)

                # Secondary supplier has a slight price variance (+2% to +10%)
                price_mult = 1.0 if is_pref else self.rng.uniform(1.02, 1.10)
                uprice = Decimal(f"{sku['unit_cost'] * price_mult:.4f}")
                lead_days = self.rng.choice([7, 14, 21, 28, 35])
                moq = self.rng.choice([50, 100, 200, 500])

                self.supplier_skus.append({
                    "id": str(ssku_id),
                    "business_id": bid,
                    "supplier_id": sup["id"],
                    "sku_id": sku["id"],
                    "unit_price": float(uprice),
                    "moq": moq,
                    "pack_size": max(1, moq // 5),
                    "lead_time_days": lead_days,
                    "is_preferred": is_pref,
                    "effective_from": self.base_date.isoformat(),
                    "effective_to": None,
                    "created_at": self.base_date.isoformat(),
                    "updated_at": self.base_date.isoformat(),
                })

    # -------------------------------------------------------------------------
    # 5. BOM & Substitute Relationships
    # -------------------------------------------------------------------------
    def _gen_5_boms_and_substitutes(self):
        fgs = [s for s in self.skus if s["sku_type"] == SKUType.FINISHED_GOOD.value]
        subs = [s for s in self.skus if s["sku_type"] == SKUType.SUBASSEMBLY.value]
        rms = [s for s in self.skus if s["sku_type"] == SKUType.RAW_MATERIAL.value]

        if not subs:
            subs = rms[:max(1, len(rms)//2)]
        if not rms:
            rms = self.skus

        bom_idx = 0
        bom_comp_idx = 0

        # Create BOM for Finished Goods
        for fg in fgs:
            bom_idx += 1
            bom_bid = f"BOM-{bom_idx:06d}"
            bom_id = make_deterministic_uuid("boms", bom_bid)

            self.boms.append({
                "id": str(bom_id),
                "business_id": bom_bid,
                "parent_sku_id": fg["id"],
                "bom_version": "v1.0",
                "description": f"Standard BOM for {fg['sku_code']}",
                "is_active": True,
                "effective_from": self.base_date.isoformat(),
                "effective_to": None,
                "created_at": self.base_date.isoformat(),
                "updated_at": self.base_date.isoformat(),
            })

            # Finished good requires 1-2 Subassemblies and 2-3 Raw Materials
            n_sub_needed = min(len(subs), self.rng.randint(1, 2))
            n_rm_needed = min(len(rms), self.rng.randint(2, 3))
            comp_sample = self.rng.sample(subs, n_sub_needed) + self.rng.sample(rms, n_rm_needed)

            for comp in comp_sample:
                bom_comp_idx += 1
                comp_bid = f"BOMC-{bom_comp_idx:06d}"
                comp_id = make_deterministic_uuid("bom_components", comp_bid)
                qty_per = Decimal(f"{self.rng.choice([1.0, 2.0, 4.0]):.4f}")
                scrap = Decimal(f"{self.rng.uniform(0.005, 0.025):.4f}")

                self.bom_components.append({
                    "id": str(comp_id),
                    "business_id": comp_bid,
                    "bom_id": str(bom_id),
                    "component_sku_id": comp["id"],
                    "quantity_per_parent": float(qty_per),
                    "scrap_percentage": float(scrap),
                    "lead_time_offset_days": self.rng.choice([1, 2, 3]),
                    "created_at": self.base_date.isoformat(),
                    "updated_at": self.base_date.isoformat(),
                })

        # Create Substitute SKUs for ~25% of Raw Materials
        subst_idx = 0
        if len(rms) >= 2:
            eligible_rms = self.rng.sample(rms, max(1, int(len(rms) * 0.25)))
            for pri_rm in eligible_rms:
                candidates = [r for r in rms if r["id"] != pri_rm["id"] and r["category"] == pri_rm["category"]]
                if not candidates:
                    candidates = [r for r in rms if r["id"] != pri_rm["id"]]
                if candidates:
                    subst_idx += 1
                    sub_rm = self.rng.choice(candidates)
                    subst_bid = f"SUB-{subst_idx:06d}"
                    subst_id = make_deterministic_uuid("substitute_skus", subst_bid)

                    self.substitute_skus.append({
                        "id": str(subst_id),
                        "business_id": subst_bid,
                        "primary_sku_id": pri_rm["id"],
                        "substitute_sku_id": sub_rm["id"],
                        "conversion_factor": 1.0,
                        "preference_rank": 1,
                        "is_bidirectional": True,
                        "effective_from": self.base_date.isoformat(),
                        "effective_to": None,
                        "created_at": self.base_date.isoformat(),
                        "updated_at": self.base_date.isoformat(),
                    })

    # -------------------------------------------------------------------------
    # 6. Forecast Demand
    # -------------------------------------------------------------------------
    def _gen_6_forecast_demand(self):
        fgs = [s for s in self.skus if s["sku_type"] == SKUType.FINISHED_GOOD.value]
        if not fgs:
            fgs = self.skus[:max(1, len(self.skus)//4)]

        # Demand is generated across all DC and WAREHOUSE locations
        demand_locs = [loc for loc in self.locations if loc["location_type"] in [LocationType.DC.value, LocationType.WAREHOUSE.value]]
        if not demand_locs:
            demand_locs = self.locations

        dem_idx = 0
        total_weeks = self.scale.weeks

        for sku in fgs:
            base_demand = self.rng.randint(60, 450)
            for loc in demand_locs:
                for w in range(1, total_weeks + 1):
                    dem_idx += 1
                    w_str = self.get_week_str(w)
                    bid = f"DEM-{sku['business_id']}-{loc['business_id']}-{w_str}"
                    dem_id = make_deterministic_uuid("forecast_demands", bid)

                    # Seasonal sinusoidal pattern (period = 52 weeks)
                    seasonal = 1.0 + 0.25 * math.sin(2.0 * math.pi * (w % 52) / 52.0)
                    # Gaussian noise with seed
                    noise = float(self.np_rng.normal(1.0, 0.08))

                    # 3% chance of natural promotional demand spike
                    spike = 1.6 if self.rng.random() < 0.03 else 1.0

                    qty = max(10, int(base_demand * seasonal * noise * spike))
                    p50 = max(10, int(qty * 0.95))
                    p90 = max(p50, int(qty * 1.15))

                    self.forecast_demands.append({
                        "id": str(dem_id),
                        "business_id": bid,
                        "sku_id": sku["id"],
                        "location_id": loc["id"],
                        "week_bucket": w_str,
                        "forecast_qty": qty,
                        "confidence_p50": p50,
                        "confidence_p90": p90,
                        "version": "v1.0",
                        "created_at": self.base_date.isoformat(),
                        "updated_at": self.base_date.isoformat(),
                    })

    # -------------------------------------------------------------------------
    # 7. Opening Inventory & Ledger Transactions
    # -------------------------------------------------------------------------
    def _gen_7_opening_inventory(self):
        inv_idx = 0
        txn_idx = 0

        for sku in self.skus:
            for loc in self.locations:
                inv_idx += 1
                bid = f"INV-{sku['business_id']}-{loc['business_id']}"
                inv_id = make_deterministic_uuid("inventories", bid)

                # Estimate typical weekly requirement
                avg_weekly = 80 if sku["sku_type"] == SKUType.FINISHED_GOOD.value else 250
                safety_stock = int(avg_weekly * 1.5)
                reorder_point = int(avg_weekly * 2.5)

                # Distribution: ~80% healthy buffer, ~20% low/tight to create realistic planning challenges
                is_tight = (inv_idx % 5 == 0)
                on_hand = int(avg_weekly * (0.6 if is_tight else self.rng.uniform(2.5, 5.0)))
                allocated = int(on_hand * self.rng.uniform(0.05, 0.20))

                self.inventories.append({
                    "id": str(inv_id),
                    "business_id": bid,
                    "sku_id": sku["id"],
                    "location_id": loc["id"],
                    "on_hand_qty": on_hand,
                    "allocated_qty": allocated,
                    "safety_stock_qty": safety_stock,
                    "reorder_point": reorder_point,
                    "last_counted_at": self.base_date.isoformat(),
                    "created_at": self.base_date.isoformat(),
                    "updated_at": self.base_date.isoformat(),
                })

                # Initial ledger transaction establishing the physical balance
                txn_idx += 1
                tx_bid = f"TXN-{txn_idx:06d}"
                tx_id = make_deterministic_uuid("inventory_transactions", tx_bid)

                self.inventory_transactions.append({
                    "id": str(tx_id),
                    "business_id": tx_bid,
                    "sku_id": sku["id"],
                    "location_id": loc["id"],
                    "transaction_type": InventoryTransactionType.RECEIPT.value,
                    "quantity": on_hand,
                    "balance_after": on_hand,
                    "reference_id": "CYCLE_COUNT_BASELINE",
                    "notes": "Opening baseline physical inventory audit count",
                    "created_at": self.base_date.isoformat(),
                })

    # -------------------------------------------------------------------------
    # 8. Supplier Capacity
    # -------------------------------------------------------------------------
    def _gen_8_supplier_capacity(self):
        cap_idx = 0
        total_weeks = self.scale.weeks

        # Generate capacity for all active supplier_skus
        for ssku in self.supplier_skus:
            # Base capacity sized comfortably above typical requirements
            base_cap = self.rng.choice([1500, 2500, 5000, 10000])
            for w in range(1, total_weeks + 1):
                cap_idx += 1
                w_str = self.get_week_str(w)
                bid = f"CAP-{ssku['business_id']}-{w_str}"
                cap_id = make_deterministic_uuid("supplier_capacities", bid)
                surge = int(base_cap * 0.25)

                self.supplier_capacities.append({
                    "id": str(cap_id),
                    "business_id": bid,
                    "supplier_id": ssku["supplier_id"],
                    "sku_id": ssku["sku_id"],
                    "week_bucket": w_str,
                    "max_capacity_units": base_cap,
                    "committed_units": 0,  # updated during PO generation
                    "surge_capacity_units": surge,
                    "created_at": self.base_date.isoformat(),
                    "updated_at": self.base_date.isoformat(),
                })

    # -------------------------------------------------------------------------
    # 9. Lead Times (Transportation Lanes)
    # -------------------------------------------------------------------------
    def _gen_9_lead_times(self):
        lt_idx = 0
        locs = self.locations

        # Connect every location to every other location (mesh network)
        for origin in locs:
            for dest in locs:
                if origin["id"] == dest["id"]:
                    continue

                lt_idx += 1
                bid = f"LT-{lt_idx:06d}"
                lt_id = make_deterministic_uuid("lead_times", bid)

                # Distance heuristic based on country / IDs
                same_country = (origin["country"] == dest["country"])
                transit = self.rng.randint(1, 4) if same_country else self.rng.randint(7, 21)
                cost = Decimal(f"{self.rng.uniform(0.5, 3.5):.4f}")

                self.lead_times.append({
                    "id": str(lt_id),
                    "business_id": bid,
                    "origin_location_id": origin["id"],
                    "destination_location_id": dest["id"],
                    "transport_mode": TransportMode.ROAD.value if same_country else TransportMode.AIR.value,
                    "transit_days": transit,
                    "variability_days": 1 if same_country else 3,
                    "cost_per_unit": float(cost),
                    "effective_from": self.base_date.isoformat(),
                    "effective_to": None,
                    "created_at": self.base_date.isoformat(),
                    "updated_at": self.base_date.isoformat(),
                })

    # -------------------------------------------------------------------------
    # 10. Production Capacity & Scheduled MPS
    # -------------------------------------------------------------------------
    def _gen_10_production_capacity(self):
        fgs = [s for s in self.skus if s["sku_type"] == SKUType.FINISHED_GOOD.value]
        plants = [loc for loc in self.locations if loc["location_type"] == LocationType.PLANT.value]
        if not plants:
            plants = self.locations[:1]

        prod_idx = 0
        total_weeks = self.scale.weeks

        for fg in fgs:
            for plant in plants:
                for w in range(1, total_weeks + 1):
                    prod_idx += 1
                    w_str = self.get_week_str(w)
                    bid = f"PROD-{fg['business_id']}-{plant['business_id']}-{w_str}"
                    prod_id = make_deterministic_uuid("production_plans", bid)
                    qty = self.rng.randint(100, 400)

                    self.production_plans.append({
                        "id": str(prod_id),
                        "business_id": bid,
                        "sku_id": fg["id"],
                        "location_id": plant["id"],
                        "week_bucket": w_str,
                        "planned_quantity": qty,
                        "status": ProductionPlanStatus.PLANNED.value,
                        "work_center_id": f"WC-LINE-{(prod_idx % 3) + 1:02d}",
                        "created_at": self.base_date.isoformat(),
                        "updated_at": self.base_date.isoformat(),
                    })

    # -------------------------------------------------------------------------
    # 11. Purchase Orders
    # -------------------------------------------------------------------------
    def _gen_11_purchase_orders(self):
        n_pos = self.scale.purchase_orders
        statuses = [PurchaseOrderStatus.PLACED, PurchaseOrderStatus.IN_TRANSIT, PurchaseOrderStatus.DRAFT]

        for i in range(1, n_pos + 1):
            bid = f"PO-2026-{i:06d}"
            po_id = make_deterministic_uuid("purchase_orders", bid)
            sup = self.rng.choice(self.suppliers)
            status = statuses[(i - 1) % len(statuses)]
            order_dt = self.base_date + timedelta(days=self.rng.randint(0, 14))

            self.purchase_orders.append({
                "id": str(po_id),
                "business_id": bid,
                "po_number": f"PO-2026-{i:06d}",
                "supplier_id": sup["id"],
                "status": status.value,
                "order_date": order_dt.isoformat(),
                "total_amount": 0.0,  # computed from lines in step 12
                "created_at": self.base_date.isoformat(),
                "updated_at": self.base_date.isoformat(),
            })

    # -------------------------------------------------------------------------
    # 12. Purchase Order Lines
    # -------------------------------------------------------------------------
    def _gen_12_purchase_order_lines(self):
        line_idx = 0
        total_weeks = self.scale.weeks

        # Map supplier_skus for quick lookup
        sup_sku_map = {}
        for ssku in self.supplier_skus:
            sup_sku_map.setdefault(ssku["supplier_id"], []).append(ssku)

        for po in self.purchase_orders:
            sup_id = po["supplier_id"]
            available_sskus = sup_sku_map.get(sup_id, self.supplier_skus)
            if not available_sskus:
                available_sskus = self.supplier_skus

            # 1 to 3 lines per PO
            n_lines = self.rng.randint(1, 3)
            po_total = Decimal("0.00")

            for line_no in range(1, n_lines + 1):
                line_idx += 1
                bid = f"POL-{po['business_id']}-{line_no:02d}"
                pol_id = make_deterministic_uuid("purchase_order_lines", bid)
                ssku = self.rng.choice(available_sskus)

                dest_loc = self.rng.choice(self.locations)
                ordered_qty = ssku["moq"] * self.rng.randint(1, 4)
                unit_cost = Decimal(str(ssku["unit_price"]))
                line_total = Decimal(str(ordered_qty)) * unit_cost
                po_total += line_total

                # Promised delivery date respects order date and supplier lead time
                po_order_dt = datetime.fromisoformat(po["order_date"])
                min_delivery_dt = po_order_dt + timedelta(days=ssku["lead_time_days"])
                horizon_end_days = max(1, (total_weeks * 7) - (min_delivery_dt - self.base_date).days)
                extra_days = self.rng.randint(0, min(14, horizon_end_days))
                prom_date = min_delivery_dt + timedelta(days=extra_days)

                self.purchase_order_lines.append({
                    "id": str(pol_id),
                    "business_id": bid,
                    "po_id": po["id"],
                    "line_number": line_no,
                    "sku_id": ssku["sku_id"],
                    "destination_location_id": dest_loc["id"],
                    "ordered_qty": ordered_qty,
                    "received_qty": 0,
                    "unit_cost": float(unit_cost),
                    "promised_delivery_date": prom_date.isoformat(),
                    "created_at": self.base_date.isoformat(),
                    "updated_at": self.base_date.isoformat(),
                })

            po["total_amount"] = float(po_total)

    # -------------------------------------------------------------------------
    # 13. Shipments & In-Flight Tracking
    # -------------------------------------------------------------------------
    def _gen_13_shipments(self):
        ship_idx = 0
        carriers = ["FEDEX", "DHL_EXP", "MAERSK", "UPS_FREIGHT"]

        # Generate shipment for every IN_TRANSIT purchase order
        in_transit_pos = [po for po in self.purchase_orders if po["status"] == PurchaseOrderStatus.IN_TRANSIT.value]

        # Map PO to first line destination
        po_line_dest = {line["po_id"]: line["destination_location_id"] for line in self.purchase_order_lines}

        for po in in_transit_pos:
            ship_idx += 1
            bid = f"SHIP-2026-{ship_idx:06d}"
            ship_id = make_deterministic_uuid("shipments", bid)
            carrier = carriers[ship_idx % len(carriers)]
            dest_loc_id = po_line_dest.get(po["id"], self.locations[0]["id"])

            etd = self.base_date + timedelta(days=self.rng.randint(1, 7))
            eta = etd + timedelta(days=self.rng.randint(3, 14))

            self.shipments.append({
                "id": str(ship_id),
                "business_id": bid,
                "po_id": po["id"],
                "carrier_code": carrier,
                "tracking_number": f"TRK-{carrier[:3]}-{ship_idx:07d}",
                "status": ShipmentStatus.IN_TRANSIT.value,
                "origin_location_id": None,
                "destination_location_id": dest_loc_id,
                "etd": etd.isoformat(),
                "eta": eta.isoformat(),
                "actual_delivery_date": None,
                "created_at": self.base_date.isoformat(),
                "updated_at": self.base_date.isoformat(),
            })


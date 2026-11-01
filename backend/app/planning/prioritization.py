"""SupplyChain IQ - Shortage Prioritization & Multi-Factor Scoring Algorithm."""

import math
from typing import Dict, Tuple

from backend.app.models.enums import LocationType, SKUType
from backend.app.planning.models import PlanningConfig, PriorityTier


class ShortagePrioritizer:
    """Computes transparent, deterministic multi-factor priority scores (0-100)

    and categorizes shortages into Critical, High, Medium, or Low priority tiers.
    """

    def __init__(self, config: PlanningConfig | None = None):
        self.config = config or PlanningConfig()

    def calculate_priority(
        self,
        days_until_stockout: int,
        shortage_qty: int,
        avg_weekly_demand: float,
        unit_cost: float,
        unit_price: float,
        sku_type: str,
        location_type: str,
        lead_time_days: int = 14,
        has_alternative_suppliers: bool = False,
        has_active_substitute: bool = False,
    ) -> Tuple[float, PriorityTier, float, Dict[str, float]]:
        """Calculate composite priority score (0-100) and assign priority tier.

        Returns:
            (priority_score, priority_tier, financial_impact, score_breakdown)
        """
        # 1. Proximity / Urgency factor (Days until stockout)
        if days_until_stockout <= 7:
            s_days = 100.0
        else:
            # Exponential decay: e.g. 14 days -> 81.0, 28 days -> 53.2, 56 days -> 22.9
            s_days = 100.0 * math.exp(-0.03 * (days_until_stockout - 7))
        s_days = max(0.0, min(100.0, s_days))

        # 2. Deficit Magnitude relative to weekly demand
        if avg_weekly_demand > 0:
            ratio = shortage_qty / avg_weekly_demand
            s_qty = min(100.0, ratio * 50.0)
        else:
            s_qty = min(100.0, (shortage_qty / 10.0) * 10.0)
        s_qty = max(0.0, min(100.0, s_qty))

        # 3. Financial Impact
        financial_impact = float(shortage_qty) * max(unit_cost, 0.0)
        s_financial = min(100.0, (financial_impact / self.config.financial_ceiling) * 100.0)
        s_financial = max(0.0, min(100.0, s_financial))

        # 4. Customer / Product Criticality
        sku_type_upper = sku_type.upper()
        if sku_type_upper == SKUType.FINISHED_GOOD.value:
            sku_crit = 100.0
        elif sku_type_upper == SKUType.SUBASSEMBLY.value:
            sku_crit = 70.0
        else:
            sku_crit = 50.0

        loc_type_upper = location_type.upper()
        if loc_type_upper in (LocationType.RETAIL.value, LocationType.DC.value):
            loc_crit = 100.0
        elif loc_type_upper == LocationType.HUB.value:
            loc_crit = 85.0
        elif loc_type_upper == LocationType.WAREHOUSE.value:
            loc_crit = 75.0
        else:  # PLANT
            loc_crit = 70.0

        s_criticality = 0.70 * sku_crit + 0.30 * loc_crit
        s_criticality = max(0.0, min(100.0, s_criticality))

        # 5. Recovery Difficulty
        # Longer supplier lead time = harder to expedite/reorder
        if lead_time_days >= 30:
            lt_factor = 60.0
        elif lead_time_days >= 15:
            lt_factor = 40.0
        elif lead_time_days >= 7:
            lt_factor = 25.0
        else:
            lt_factor = 10.0

        single_source_factor = 25.0 if not has_alternative_suppliers else 0.0
        no_substitute_factor = 15.0 if not has_active_substitute else 0.0

        s_recovery = min(100.0, lt_factor + single_source_factor + no_substitute_factor)
        s_recovery = max(0.0, min(100.0, s_recovery))

        # Weighted composite score
        composite = (
            self.config.w_days * s_days
            + self.config.w_qty * s_qty
            + self.config.w_financial * s_financial
            + self.config.w_criticality * s_criticality
            + self.config.w_recovery * s_recovery
        )
        score = round(max(0.0, min(100.0, composite)), 2)

        # Tier assignment
        if score >= self.config.threshold_critical:
            tier = PriorityTier.CRITICAL
        elif score >= self.config.threshold_high:
            tier = PriorityTier.HIGH
        elif score >= self.config.threshold_medium:
            tier = PriorityTier.MEDIUM
        else:
            tier = PriorityTier.LOW

        breakdown = {
            "days_until_stockout_score": round(s_days, 2),
            "shortage_quantity_score": round(s_qty, 2),
            "financial_impact_score": round(s_financial, 2),
            "customer_criticality_score": round(s_criticality, 2),
            "recovery_difficulty_score": round(s_recovery, 2),
        }

        return score, tier, round(financial_impact, 2), breakdown


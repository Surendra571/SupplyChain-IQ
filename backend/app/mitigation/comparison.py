"""SupplyChain IQ - Mitigation Comparison Engine.

Ranks mitigation options using the 5-tier criteria:
1. Feasibility (feasible first)
2. Recovery time (fastest lead time)
3. Total cost (lowest financial cost)
4. Service improvement (highest fill rate protected)
5. Business priority (ROI ratio)

Extracts:
- Cheapest option
- Fastest option
- Best service recovery option
- Recommended option
with clear business rationale for every recommendation.
"""

from typing import Any, Dict, List, Optional

from backend.app.mitigation.models import MitigationCandidate, MitigationComparison


class ComparisonEngine:
    """Classifies and compares candidate mitigation options for supply chain shortages."""

    def compare_options(
        self,
        shortage: Any,
        all_candidates: List[MitigationCandidate],
        optimized_selected_candidates: Optional[List[MitigationCandidate]] = None,
    ) -> MitigationComparison:
        """Rank and categorize candidates into cheapest, fastest, best service, and recommended."""
        shortage_id = shortage.business_id
        sku_code = getattr(shortage, "sku_code", "")
        loc_code = getattr(shortage, "location_code", "")
        week_bucket = getattr(shortage, "week_bucket", "")
        deficit = int(getattr(shortage, "projected_deficit_qty", 0))

        if not all_candidates:
            return MitigationComparison(
                shortage_id=shortage_id,
                sku_code=sku_code,
                location_code=loc_code,
                week_bucket=week_bucket,
                projected_deficit_qty=deficit,
                comparison_summary="No candidate mitigation options identified for this shortage.",
            )

        # 1. Rank options using the 5 mandatory criteria:
        # Feasibility (True first), Recovery time (ascending), Total cost (ascending),
        # Service level (descending), ROI ratio (descending)
        ranked_candidates = sorted(
            all_candidates,
            key=lambda c: (
                0 if c.is_feasible else 1,
                c.recovery_time_days if c.is_feasible else 9999,
                c.total_cost if c.is_feasible else 999999,
                -c.service_level_impact if c.is_feasible else 0,
                -c.roi_ratio if c.is_feasible else 0,
            ),
        )

        for rank_idx, c in enumerate(ranked_candidates, start=1):
            c.rank = rank_idx

        feasible_options = [c for c in ranked_candidates if c.is_feasible]

        cheapest: Optional[MitigationCandidate] = None
        fastest: Optional[MitigationCandidate] = None
        best_service: Optional[MitigationCandidate] = None
        recommended: Optional[MitigationCandidate] = None

        if feasible_options:
            # Cheapest: minimum total_cost
            cheapest = min(feasible_options, key=lambda c: (c.total_cost, c.recovery_time_days))

            # Fastest: minimum recovery_time_days
            fastest = min(feasible_options, key=lambda c: (c.recovery_time_days, c.total_cost))

            # Best service: maximum service_level_impact / recoverable_quantity
            best_service = max(feasible_options, key=lambda c: (c.service_level_impact, -c.total_cost))

            # Recommended: Check if OR-Tools optimization selected an option for this shortage
            optimized_map = {c.shortage_id: c for c in (optimized_selected_candidates or [])}
            if shortage_id in optimized_map:
                recommended = optimized_map[shortage_id]
            else:
                # Top-ranked feasible candidate from multi-criteria ranking
                recommended = ranked_candidates[0]

        # Generate comparison rationale
        if recommended and recommended.is_feasible:
            reason = (
                f"Recommended {recommended.action_type.value}: Recovers {recommended.recoverable_quantity} of "
                f"{deficit} units ({recommended.service_level_impact:.1f}% service protection) within "
                f"{recommended.recovery_time_days} days at a total cost of ${recommended.total_cost:,.2f} "
                f"(ROI: {recommended.roi_ratio:.2f}x). "
            )
            if cheapest and cheapest.candidate_id != recommended.candidate_id:
                reason += f"Cheaper alternative: {cheapest.action_type.value} (${cheapest.total_cost:,.2f}). "
            if fastest and fastest.candidate_id != recommended.candidate_id:
                reason += f"Faster alternative: {fastest.action_type.value} ({fastest.recovery_time_days}d). "
        else:
            reason = "No feasible mitigation option available under current network capacity, lead time, or inventory constraints."

        return MitigationComparison(
            shortage_id=shortage_id,
            sku_code=sku_code,
            location_code=loc_code,
            week_bucket=week_bucket,
            projected_deficit_qty=deficit,
            cheapest_option=cheapest,
            fastest_option=fastest,
            best_service_option=best_service,
            recommended_option=recommended,
            all_options=ranked_candidates,
            comparison_summary=reason,
        )

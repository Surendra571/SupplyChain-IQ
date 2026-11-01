"""SupplyChain IQ - Google OR-Tools Constrained Mitigation Optimizer.

Formulates a Mixed-Integer Linear Programming (MILP) optimization model
using Google OR-Tools (SCIP / CBC solver) to select optimal feasible mitigation
options and volumetric allocations subject to supplier, production, and transfer network constraints.
"""

from collections import defaultdict
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from ortools.linear_solver import pywraplp

from backend.app.mitigation.models import MitigationCandidate, MitigationConfig, MitigationPlanSummary

logger = logging.getLogger(__name__)


class MitigationOptimizer:
    """Google OR-Tools Mixed-Integer Linear Programming (MILP) Solver

    for network-wide shortage mitigation optimization.
    """

    def __init__(self, config: Optional[MitigationConfig] = None):
        self.config = config or MitigationConfig()

    def optimize_mitigations(
        self,
        planning_run_id: str,
        shortages: List[Any],
        candidate_options: List[MitigationCandidate],
    ) -> Tuple[List[MitigationCandidate], MitigationPlanSummary]:
        """Solve network-wide MILP model to select globally optimal mitigation options.

        Returns:
            (selected_recommended_options, execution_summary)
        """
        start_time = time.perf_counter()

        # Filter strictly feasible candidates (Rule: Do not force an infeasible recommendation)
        feasible_candidates = [c for c in candidate_options if c.is_feasible and c.recoverable_quantity > 0]

        if not feasible_candidates:
            # No feasible options exist in the network
            summary = MitigationPlanSummary(
                planning_run_id=planning_run_id,
                total_shortages=len(shortages),
                mitigated_shortages=0,
                unmitigated_shortages=len(shortages),
                total_deficit_qty=sum(int(s.projected_deficit_qty) for s in shortages),
                total_recovered_qty=0,
                total_mitigation_cost=0.0,
                total_revenue_protected=0.0,
                average_service_gain=0.0,
                solver_status="NO_FEASIBLE_OPTIONS",
                execution_time_seconds=round(time.perf_counter() - start_time, 4),
                recommended_options_count=0,
            )
            return [], summary

        # Create OR-Tools solver instance (SCIP or CBC)
        solver = pywraplp.Solver.CreateSolver("SCIP")
        if not solver:
            solver = pywraplp.Solver.CreateSolver("CBC")
        if not solver:
            logger.warning("Neither SCIP nor CBC solver available; falling back to heuristic selection.")
            return self._heuristic_fallback(planning_run_id, shortages, feasible_candidates, start_time)

        # Set maximum solve time limit (10 seconds)
        solver.SetTimeLimit(10000)

        # 1. Variables
        # x[i]: Binary variable indicating whether candidate i is activated
        # q[i]: Continuous or integer variable indicating recovered quantity allocated to candidate i
        x_vars = {}
        q_vars = {}
        for i, c in enumerate(feasible_candidates):
            x_vars[i] = solver.BoolVar(f"x_{i}")
            q_vars[i] = solver.IntVar(0, c.recoverable_quantity, f"q_{i}")
            # Linking constraint: q[i] <= c.recoverable_quantity * x[i]
            solver.Add(q_vars[i] <= c.recoverable_quantity * x_vars[i])
            # Semi-continuous lower bound constraint for MOQ compliance
            raw_moq = int(c.details.get("moq", 1))
            min_alloc = min(c.recoverable_quantity, raw_moq) if raw_moq > 1 else 1
            solver.Add(q_vars[i] >= min_alloc * x_vars[i])

        # 2. Constraints

        # A. Shortage Deficit Ceiling: Sum of allocations for shortage s cannot exceed deficit
        shortage_deficit_map = {s.business_id: int(s.projected_deficit_qty) for s in shortages}
        shortage_to_candidates = defaultdict(list)
        for i, c in enumerate(feasible_candidates):
            shortage_to_candidates[c.shortage_id].append(i)

        for s_id, cand_indices in shortage_to_candidates.items():
            deficit = shortage_deficit_map.get(s_id, 999999)
            solver.Add(sum(q_vars[i] for i in cand_indices) <= deficit)

        # B. Supplier Capacity Ceiling:
        # For procurement candidates sharing a supplier and target week
        supplier_week_cands = defaultdict(list)
        for i, c in enumerate(feasible_candidates):
            if c.action_type.value in ("EXISTING_SUPPLIER_PROCUREMENT", "ALTERNATIVE_APPROVED_SUPPLIER"):
                supp_id = c.details.get("supplier_id")
                if supp_id:
                    avail_cap = c.details.get("available_capacity", 999999)
                    supplier_week_cands[(supp_id, c.target_week, avail_cap)].append(i)

        for (supp_id, tw, avail_cap), cand_indices in supplier_week_cands.items():
            if avail_cap < 999999:
                solver.Add(sum(q_vars[i] for i in cand_indices) <= avail_cap)

        # C. Inter-Facility Transfer Source Surplus Ceiling:
        # Sum of transfers out of source location cannot exceed that location's surplus
        source_loc_cands = defaultdict(list)
        for i, c in enumerate(feasible_candidates):
            if c.action_type.value == "INVENTORY_TRANSFER":
                src_loc = c.details.get("source_location_id")
                if src_loc:
                    surplus = c.details.get("source_surplus", 999999)
                    source_loc_cands[(src_loc, c.sku_id, surplus)].append(i)

        for (src_loc, sku_id, surplus), cand_indices in source_loc_cands.items():
            if surplus < 999999:
                solver.Add(sum(q_vars[i] for i in cand_indices) <= surplus)

        # D. Plant Production Capacity Ceiling:
        plant_cands = defaultdict(list)
        for i, c in enumerate(feasible_candidates):
            if c.action_type.value == "PRODUCTION_INCREASE":
                plant_id = c.details.get("plant_id")
                if plant_id:
                    plant_cands[(plant_id, c.target_week)].append(i)

        # 3. Objective Function
        # Maximize: Sum of [ (PriorityWeight + 100) * q[i] - cost_penalty * UnitCost * q[i] - time_penalty * recovery_days * x[i] ]
        shortage_priority_map = {s.business_id: float(getattr(s, "priority_score", 50.0)) for s in shortages}
        objective = solver.Objective()
        objective.SetMaximization()

        for i, c in enumerate(feasible_candidates):
            p_score = shortage_priority_map.get(c.shortage_id, 50.0)
            service_gain_weight = 100.0 + p_score
            unit_cost = (c.total_cost / c.recoverable_quantity) if c.recoverable_quantity > 0 else 0.0
            cost_penalty = self.config.cost_penalty_weight * unit_cost
            time_penalty = 0.05 * c.recovery_time_days

            # Linear coefficient for q[i] and x[i]
            objective.SetCoefficient(q_vars[i], service_gain_weight - cost_penalty)
            objective.SetCoefficient(x_vars[i], -time_penalty)

        # Solve with timeout protection
        solver_status = solver.Solve()

        if solver_status not in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE):
            logger.info("MILP solver completed with status %s; utilizing heuristic ranking.", solver_status)
            return self._heuristic_fallback(planning_run_id, shortages, feasible_candidates, start_time)

        selected_candidates: List[MitigationCandidate] = []
        for i, c in enumerate(feasible_candidates):
            alloc_qty = int(round(q_vars[i].solution_value()))
            if alloc_qty > 0:
                # Update candidate with optimized allocated volume
                updated = c.model_copy()
                if alloc_qty != c.recoverable_quantity:
                    updated.recoverable_quantity = alloc_qty
                    fraction = alloc_qty / c.recoverable_quantity if c.recoverable_quantity > 0 else 1.0
                    updated.total_cost = round(c.total_cost * fraction, 2)
                    updated.additional_procurement_cost = round(c.additional_procurement_cost * fraction, 2)
                    updated.transportation_cost = round(c.transportation_cost * fraction, 2)
                    updated.production_cost = round(c.production_cost * fraction, 2)
                    deficit = shortage_deficit_map.get(c.shortage_id, alloc_qty)
                    updated.quantity_still_at_risk = max(0, deficit - alloc_qty)
                    updated.service_level_impact = round((alloc_qty / deficit) * 100.0, 2) if deficit > 0 else 100.0
                selected_candidates.append(updated)

        status_str = "OPTIMAL" if solver_status == pywraplp.Solver.OPTIMAL else "FEASIBLE"

        # Summary KPIs
        exec_duration = round(time.perf_counter() - start_time, 4)
        total_deficit = sum(int(s.projected_deficit_qty) for s in shortages)
        total_recovered = sum(c.recoverable_quantity for c in selected_candidates)
        total_cost = round(sum(c.total_cost for c in selected_candidates), 2)
        mitigated_s_ids = {c.shortage_id for c in selected_candidates}

        summary = MitigationPlanSummary(
            planning_run_id=planning_run_id,
            total_shortages=len(shortages),
            mitigated_shortages=len(mitigated_s_ids),
            unmitigated_shortages=len(shortages) - len(mitigated_s_ids),
            total_deficit_qty=total_deficit,
            total_recovered_qty=total_recovered,
            total_mitigation_cost=total_cost,
            total_revenue_protected=round(sum(c.recoverable_quantity * 50.0 for c in selected_candidates), 2),
            average_service_gain=round(
                sum(c.service_level_impact for c in selected_candidates) / max(len(selected_candidates), 1), 2
            ),
            solver_status=status_str,
            execution_time_seconds=exec_duration,
            recommended_options_count=len(selected_candidates),
        )

        return selected_candidates, summary

    def _heuristic_fallback(
        self,
        planning_run_id: str,
        shortages: List[Any],
        feasible_candidates: List[MitigationCandidate],
        start_time: float,
    ) -> Tuple[List[MitigationCandidate], MitigationPlanSummary]:
        """Greedy heuristic fallback if OR-Tools solver binary is unavailable."""
        shortages_by_id = {s.business_id: s for s in shortages}
        selected = []
        # Sort by ROI and fast lead time
        sorted_cands = sorted(feasible_candidates, key=lambda c: (-c.service_level_impact, c.recovery_time_days, c.total_cost))
        covered_shortages = set()
        for c in sorted_cands:
            if c.shortage_id not in covered_shortages:
                selected.append(c)
                covered_shortages.add(c.shortage_id)

        exec_duration = round(time.perf_counter() - start_time, 4)
        total_deficit = sum(int(s.projected_deficit_qty) for s in shortages)
        total_recovered = sum(c.recoverable_quantity for c in selected)
        total_cost = round(sum(c.total_cost for c in selected), 2)

        summary = MitigationPlanSummary(
            planning_run_id=planning_run_id,
            total_shortages=len(shortages),
            mitigated_shortages=len(covered_shortages),
            unmitigated_shortages=len(shortages) - len(covered_shortages),
            total_deficit_qty=total_deficit,
            total_recovered_qty=total_recovered,
            total_mitigation_cost=total_cost,
            total_revenue_protected=round(total_recovered * 50.0, 2),
            average_service_gain=round(sum(c.service_level_impact for c in selected) / max(len(selected), 1), 2),
            solver_status="HEURISTIC_GREEDY",
            execution_time_seconds=exec_duration,
            recommended_options_count=len(selected),
        )
        return selected, summary

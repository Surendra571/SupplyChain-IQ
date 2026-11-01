"""SupplyChain IQ - Supply-Demand Planning Engine CLI Runner."""

import argparse
import asyncio
from pathlib import Path
import sys

from backend.app.core.database import AsyncSessionLocal
from backend.app.mitigation.service import MitigationService
from backend.app.planning.engine import SupplyDemandPlanningEngine
from backend.app.planning.models import PlanningConfig
from backend.app.planning.snapshot import PlanningSnapshotManager


async def run_cli():
    parser = argparse.ArgumentParser(description="SupplyChain IQ - Weekly Supply-Demand Planning Engine CLI")
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data/generated/starter/csv",
        help="Path to CSV dataset directory (default: data/generated/starter/csv)",
    )
    parser.add_argument(
        "--horizon",
        type=int,
        default=12,
        help="Planning horizon in weeks (default: 12)",
    )
    parser.add_argument(
        "--run-number",
        type=int,
        default=1,
        help="Sequential planning run number (default: 1)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/planning_runs",
        help="Directory to save immutable planning snapshots (default: data/planning_runs)",
    )
    parser.add_argument(
        "--persist-db",
        action="store_true",
        help="Persist planning run and shortages to PostgreSQL database",
    )
    parser.add_argument(
        "--top-shortages",
        type=int,
        default=10,
        help="Number of prioritized shortages to display in console table (default: 10)",
    )

    args = parser.parse_args()
    data_path = Path(args.data_dir)
    if not data_path.exists():
        print(f"[ERROR] Data directory not found: {data_path}")
        sys.exit(1)

    print("=" * 80)
    print("SUPPLYCHAIN IQ - SUPPLY-DEMAND PLANNING ENGINE")
    print("=" * 80)
    print(f"Data Source:        {data_path}")
    print(f"Planning Horizon:   {args.horizon} weeks")
    print(f"Planning Run ID:    RUN-{args.run_number:04d}")
    print("-" * 80)

    config = PlanningConfig(horizon_weeks=args.horizon)
    engine = SupplyDemandPlanningEngine.from_directory(data_path, config=config)

    print("[1/3] Executing time-phased Projected Available Balance simulation...")
    projections, shortages, summary = engine.run_planning(
        run_number=args.run_number,
        horizon_weeks=args.horizon,
    )

    print("[2/4] Reconciling weekly inventory balances...")
    engine.verify_balance_reconciliation(projections)
    print("  -> Week-by-week balance reconciliation: 100% VERIFIED")

    print("[3/4] Solving constrained mitigation optimization with Google OR-Tools...")
    mit_service = MitigationService(engine.data)
    comparisons, candidates, mit_summary = mit_service.generate_mitigation_plan(
        planning_run_id=summary.run_id,
        shortages=shortages,
    )
    print(f"  -> Evaluated {len(candidates):,} candidate options across 7 mitigation levers.")
    print(f"  -> OR-Tools Solver Status: {mit_summary.solver_status}")
    print(f"  -> Mitigated Shortages: {mit_summary.mitigated_shortages:,} / {mit_summary.total_shortages:,}")
    print(f"  -> Total Units Recovered: {mit_summary.total_recovered_qty:,} (Cost: ${mit_summary.total_mitigation_cost:,.2f})")

    print("[4/4] Exporting planning and mitigation run snapshots...")
    snapshot_mgr = PlanningSnapshotManager(Path(args.output_dir))
    export_path = snapshot_mgr.export_snapshot_files(summary, projections, shortages)
    mit_service.export_mitigation_snapshots(export_path, comparisons, candidates, mit_summary)
    print(f"  -> Snapshot files exported to: {export_path}")

    if args.persist_db:
        print("  -> Persisting planning run and mitigations to PostgreSQL...")
        try:
            async with AsyncSessionLocal() as session:
                run_uuid = await snapshot_mgr.persist_to_database(session, summary, shortages)
                mit_count = await mit_service.persist_to_database(session, comparisons)
                print(f"  -> Saved run {run_uuid} with {mit_count} mitigation options to PostgreSQL.")
        except Exception as e:
            print(f"  -> [WARNING] DB persistence failed: {e}")

    # Display KPI Summary
    print("\n" + "=" * 80)
    print("PLANNING RUN SUMMARY KPIs")
    print("=" * 80)
    print(f"Total Projections:           {summary.total_projections:,}")
    print(f"Total Shortages Identified:  {summary.total_shortages:,}")
    print(f"  - Critical Shortages (PAB < 0):      {summary.critical_shortages:,}")
    print(f"  - Warning (Safety Stock Gap):        {summary.warning_shortages:,}")
    print(f"Total Demand Shortage Qty:   {summary.total_demand_shortage_qty:,} units")
    print(f"Total Safety Stock Gap Qty:  {summary.total_safety_stock_gap_qty:,} units")
    print(f"Total Financial Impact:      ${summary.total_financial_impact:,.2f}")
    print(f"Simulation Duration:         {summary.execution_time_seconds:.4f} seconds")
    print(f"Optimization Duration:       {mit_summary.execution_time_seconds:.4f} seconds")

    print("\nRoot Cause Breakdown:")
    for cause, cnt in sorted(summary.root_cause_breakdown.items(), key=lambda x: -x[1]):
        print(f"  {cause:<32}: {cnt:>5}")

    print("\nPriority Tier Breakdown:")
    for tier, cnt in sorted(summary.priority_breakdown.items(), key=lambda x: -x[1]):
        print(f"  {tier:<16}: {cnt:>5}")

    # Display top shortages & Recommended Mitigations
    if comparisons and args.top_shortages > 0:
        shortages_by_id = {s.business_id: s for s in shortages}
        sorted_comps = sorted(
            comparisons,
            key=lambda c: (
                -(shortages_by_id.get(c.shortage_id).priority_score if c.shortage_id in shortages_by_id else 0),
                shortages_by_id.get(c.shortage_id).days_until_stockout if c.shortage_id in shortages_by_id else 0,
            ),
        )[:args.top_shortages]

        print("\n" + "=" * 80)
        print(f"TOP {min(len(sorted_comps), args.top_shortages)} MITIGATION RECOMMENDATIONS & TRADE-OFF COMPARISON")
        print("=" * 80)
        for idx, comp in enumerate(sorted_comps, start=1):
            s = shortages_by_id.get(comp.shortage_id)
            print(f"[{idx}] {comp.shortage_id} | {comp.sku_code} @ {comp.location_code} | Week: {comp.week_bucket} | Deficit: {comp.projected_deficit_qty:,} units")
            rec = comp.recommended_option
            if rec and rec.is_feasible:
                print(f"  -> RECOMMENDED: {rec.action_type.value} | Recover: {rec.recoverable_quantity:,} units | Cost: ${rec.total_cost:,.2f} | Time: {rec.recovery_time_days}d | ROI: {rec.roi_ratio:.2f}x")
            else:
                print("  -> RECOMMENDED: None feasible under current constraints.")
            if comp.cheapest_option:
                print(f"     Cheapest:    {comp.cheapest_option.action_type.value} (${comp.cheapest_option.total_cost:,.2f})")
            if comp.fastest_option:
                print(f"     Fastest:     {comp.fastest_option.action_type.value} ({comp.fastest_option.recovery_time_days}d)")
            if comp.best_service_option:
                print(f"     Best Service:{comp.best_service_option.action_type.value} ({comp.best_service_option.service_level_impact:.1f}%)")
            print(f"  -> Reason: {comp.comparison_summary}\n")

    print("[SUCCESS] Planning and mitigation optimization completed successfully.")


def main():
    asyncio.run(run_cli())


if __name__ == "__main__":
    main()

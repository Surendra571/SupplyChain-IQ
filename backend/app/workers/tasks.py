"""SupplyChain IQ - Celery Tasks for Supply Chain Planning Engine."""

import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import traceback
from typing import Any, Dict

from backend.app.core.database import AsyncSessionLocal, SessionLocal
from backend.app.mitigation.service import MitigationService
from backend.app.models.enums import PlanningRunStatus
from backend.app.models.planning import PlanningRun
from backend.app.planning.engine import SupplyDemandPlanningEngine
from backend.app.planning.models import PlanningConfig
from backend.app.planning.snapshot import PlanningSnapshotManager
from backend.app.workers.celery_app import celery_app


def run_planning_job_sync(
    run_number: int,
    horizon_weeks: int = 12,
    data_dir: str = "data/generated/starter/csv",
    output_dir: str = "data/planning_runs",
    persist_db: bool = True,
) -> Dict[str, Any]:
    """Synchronous execution routine invoked by Celery or ThreadPool."""
    data_path = Path(data_dir)
    if not data_path.exists():
        raise FileNotFoundError(f"Data directory not found: {data_path}")

    config = PlanningConfig(horizon_weeks=horizon_weeks)
    engine = SupplyDemandPlanningEngine.from_directory(data_path, config=config)

    # 1. MRP Simulation
    projections, shortages, summary = engine.run_planning(
        run_number=run_number,
        horizon_weeks=horizon_weeks,
    )
    engine.verify_balance_reconciliation(projections)

    # 2. Optimization
    mit_service = MitigationService(engine.data)
    comparisons, candidates, mit_summary = mit_service.generate_mitigation_plan(
        planning_run_id=summary.run_id,
        shortages=shortages,
    )

    # 3. Snapshot Export
    snapshot_mgr = PlanningSnapshotManager(Path(output_dir))
    export_path = snapshot_mgr.export_snapshot_files(summary, projections, shortages)
    mit_service.export_mitigation_snapshots(export_path, comparisons, candidates, mit_summary)

    # 4. DB Persistence
    run_uuid_str = None
    if persist_db and AsyncSessionLocal is not None:
        async def _persist():
            async with AsyncSessionLocal() as session:
                ruuid = await snapshot_mgr.persist_to_database(session, summary, shortages)
                await mit_service.persist_to_database(session, comparisons)
                return str(ruuid)

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Already in async loop
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    run_uuid_str = executor.submit(lambda: asyncio.run(_persist())).result()
            else:
                run_uuid_str = asyncio.run(_persist())
        except Exception:
            run_uuid_str = asyncio.run(_persist())

    return {
        "run_id": summary.run_id,
        "run_number": run_number,
        "run_uuid": run_uuid_str,
        "status": "COMPLETED",
        "total_shortages": summary.total_shortages,
        "critical_shortages": summary.critical_shortages,
        "total_financial_impact": summary.total_financial_impact,
        "export_path": str(export_path),
        "solver_status": mit_summary.solver_status,
        "mitigated_shortages": mit_summary.mitigated_shortages,
    }


@celery_app.task(bind=True, name="tasks.execute_planning_run")
def execute_planning_run_task(
    self,
    run_number: int,
    horizon_weeks: int = 12,
    data_dir: str = "data/generated/starter/csv",
    output_dir: str = "data/planning_runs",
    persist_db: bool = True,
):
    """Celery background worker task."""
    try:
        self.update_state(state="PROGRESS", meta={"progress": 25, "stage": "MRP_SIMULATION"})
        result = run_planning_job_sync(
            run_number=run_number,
            horizon_weeks=horizon_weeks,
            data_dir=data_dir,
            output_dir=output_dir,
            persist_db=persist_db,
        )
        self.update_state(state="SUCCESS", meta={"progress": 100, "result": result})
        return result
    except Exception as exc:
        self.update_state(
            state="FAILURE",
            meta={"exc_type": type(exc).__name__, "exc_message": str(exc), "traceback": traceback.format_exc()},
        )
        raise exc


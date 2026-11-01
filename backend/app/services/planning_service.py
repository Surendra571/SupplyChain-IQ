"""SupplyChain IQ - Planning Orchestration Service."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.exceptions import EntityNotFoundError
from backend.app.models.enums import PlanningRunStatus
from backend.app.models.master_data import Location, SKU
from backend.app.models.planning import PlanningRun, Shortage
from backend.app.planning.engine import SupplyDemandPlanningEngine
from backend.app.planning.models import PlanningConfig
from backend.app.repositories.planning_repo import PlanningRepository
from backend.app.schemas.planning_api import PlanningRunDetailResponse, ShortagePABDetailResponse, TimePhasedPABPoint
from backend.app.workers.tasks import run_planning_job_sync

_executor = ThreadPoolExecutor(max_workers=4)


class PlanningService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = PlanningRepository(session)

    async def get_run_detail(self, run_id: str) -> PlanningRunDetailResponse:
        run = await self.repo.get_run(run_id)
        if not run:
            raise EntityNotFoundError("PlanningRun", run_id)

        summary_dict = json.loads(run.summary_json) if run.summary_json else {}

        return PlanningRunDetailResponse(
            id=run.id,
            business_id=run.business_id,
            run_number=run.run_number,
            status=run.status,
            horizon_weeks=run.horizon_weeks,
            started_at=run.started_at,
            completed_at=run.completed_at,
            execution_time_seconds=summary_dict.get("execution_time_seconds"),
            total_projections=summary_dict.get("total_projections", 0),
            total_shortages=summary_dict.get("total_shortages", 0),
            critical_shortages=summary_dict.get("critical_shortages", 0),
            warning_shortages=summary_dict.get("warning_shortages", 0),
            total_demand_shortage_qty=summary_dict.get("total_demand_shortage_qty", 0),
            total_safety_stock_gap_qty=summary_dict.get("total_safety_stock_gap_qty", 0),
            total_financial_impact=summary_dict.get("total_financial_impact", 0.0),
            root_cause_breakdown=summary_dict.get("root_cause_breakdown", {}),
            priority_breakdown=summary_dict.get("priority_breakdown", {}),
            is_superseded=run.is_superseded,
            created_at=run.created_at,
            updated_at=run.updated_at,
        )

    async def get_latest_run(self) -> Optional[PlanningRunDetailResponse]:
        run = await self.repo.get_latest_run()
        if not run:
            return None
        return await self.get_run_detail(str(run.id))

    async def trigger_run(
        self,
        horizon_weeks: int = 12,
        data_dir: Optional[str] = None,
        persist_db: bool = True,
        use_celery: bool = False,
    ) -> Dict[str, Any]:
        """Trigger a planning run either via Celery or background ThreadPool."""
        # Find next sequential run number
        latest = await self.repo.get_latest_run()
        next_run_number = (latest.run_number + 1) if latest else 1

        resolved_data_dir = data_dir or "data/generated/starter/csv"

        if use_celery:
            from backend.app.workers.tasks import execute_planning_run_task
            task = execute_planning_run_task.delay(
                run_number=next_run_number,
                horizon_weeks=horizon_weeks,
                data_dir=resolved_data_dir,
                persist_db=persist_db,
            )
            return {
                "task_id": task.id,
                "run_number": next_run_number,
                "status": "QUEUED",
                "message": f"Planning run {next_run_number} queued via Celery.",
            }

        # Otherwise execute synchronously / in worker thread
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            _executor,
            lambda: run_planning_job_sync(
                run_number=next_run_number,
                horizon_weeks=horizon_weeks,
                data_dir=resolved_data_dir,
                persist_db=persist_db,
            ),
        )
        return {
            "run_number": next_run_number,
            "status": "COMPLETED",
            "result": result,
            "message": f"Planning run {next_run_number} executed successfully.",
        }

    async def get_shortage_pab(self, shortage_id: str) -> ShortagePABDetailResponse:
        """Compute the 12-week time-phased PAB curve for the SKU-Location of this shortage."""
        item = await self.repo.get_shortage(shortage_id)
        if not item:
            raise EntityNotFoundError("Shortage", shortage_id)
        shortage, sku, loc = item

        # Run DuckDB simulation for this SKU-location from directory
        data_path = Path("data/generated/starter/csv")
        config = PlanningConfig(horizon_weeks=12)
        engine = SupplyDemandPlanningEngine.from_directory(data_path, config=config)
        projections, _, _ = engine.run_planning(run_number=1, horizon_weeks=12)

        # Filter points matching this sku and location
        matching = [
            p for p in projections
            if p.sku_code == sku.sku_code and p.location_code == loc.location_code
        ]
        matching.sort(key=lambda p: p.week_index)

        points = [
            TimePhasedPABPoint(
                week_bucket=p.week_bucket,
                week_index=p.week_index,
                opening_balance=p.opening_pab,
                forecast_demand=p.forecast_demand,
                scheduled_receipts=p.purchase_receipts,
                planned_production=p.production_receipts,
                transfers_in=p.transfers_in,
                transfers_out=p.transfers_out,
                allocated_qty=p.allocations,
                safety_stock=p.safety_stock,
                projected_available_balance=p.closing_pab,
                demand_shortage=p.demand_shortage,
                safety_stock_gap=p.safety_stock_gap,
                stockout_risk=p.closing_pab < 0,
            )
            for p in matching
        ]

        return ShortagePABDetailResponse(
            sku_code=sku.sku_code,
            sku_name=sku.name,
            location_code=loc.location_code,
            location_name=loc.name,
            shortage_week=shortage.week_bucket,
            points=points,
        )

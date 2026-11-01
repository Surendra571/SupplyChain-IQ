"""SupplyChain IQ - Celery Worker Configuration."""

from celery import Celery
from backend.app.core.config import settings

celery_app = Celery(
    "supplychain_iq_workers",
    broker=settings.celery_broker,
    backend=settings.celery_backend,
    include=["backend.app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=1800,  # 30 minutes for large-scale MRP runs
    task_soft_time_limit=1500,
    worker_concurrency=4,
)


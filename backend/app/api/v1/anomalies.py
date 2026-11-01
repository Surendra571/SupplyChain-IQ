"""SupplyChain IQ - Data Quality & Anomalies Router."""

from typing import Annotated
from fastapi import APIRouter, Depends
from backend.app.api.deps import get_current_user, require_roles
from backend.app.core.rbac import UserRole
from backend.app.schemas.anomaly_api import AnomalyScanResponse
from backend.app.services.anomaly_service import AnomalyService

router = APIRouter(prefix="/anomalies", tags=["Data Quality & Integrity Engine"])


@router.get("", response_model=AnomalyScanResponse, summary="Get Data Quality Anomaly Report")
async def get_data_quality_report(
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Retrieve comprehensive data quality scan results including the 5 deliberate anomaly scenarios."""
    service = AnomalyService()
    return service.run_scan(include_evaluation=True)


@router.post(
    "/scan",
    response_model=AnomalyScanResponse,
    summary="Trigger Comprehensive Data Quality Integrity Scan",
)
async def trigger_data_quality_scan(
    current_user: Annotated[
        dict,
        Depends(require_roles([UserRole.OPERATIONS_MANAGER, UserRole.ADMINISTRATOR])),
    ],
):
    """Trigger an active data quality integrity scan across all 12 validation suites."""
    service = AnomalyService()
    return service.run_scan(include_evaluation=True)


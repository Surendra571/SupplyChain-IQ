"""SupplyChain IQ - API v1 Master Router."""

from fastapi import APIRouter

from backend.app.api.v1.anomalies import router as anomalies_router
from backend.app.api.v1.audit_events import router as audit_router
from backend.app.api.v1.auth import router as auth_router
from backend.app.api.v1.decisions import router as decisions_router
from backend.app.api.v1.master_data import router as master_data_router
from backend.app.api.v1.mitigations import router as mitigations_router
from backend.app.api.v1.ops import router as ops_router
from backend.app.api.v1.planning_runs import router as planning_router
from backend.app.api.v1.shortages import router as shortages_router

api_v1_router = APIRouter(prefix="/v1")

api_v1_router.include_router(auth_router)
api_v1_router.include_router(planning_router)
api_v1_router.include_router(shortages_router)
api_v1_router.include_router(mitigations_router)
api_v1_router.include_router(decisions_router)
api_v1_router.include_router(anomalies_router)
api_v1_router.include_router(audit_router)
api_v1_router.include_router(master_data_router)
api_v1_router.include_router(ops_router)


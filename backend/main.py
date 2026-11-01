"""SupplyChain IQ - Main FastAPI Application."""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api.v1.router import api_v1_router
from backend.app.core.config import settings
from backend.app.core.exceptions import SupplyChainIQException, domain_exception_handler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown hooks."""
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="""
# SupplyChain IQ API

Intelligent Enterprise Supply Chain Planning platform matching forecast demand
against inventory, supplier capacity, lead times, production constraints, and logistics availability.

### Key Capabilities:
* **Weekly MRP Simulation**: Multi-echelon time-phased Projected Available Balance (PAB).
* **Prioritized Shortage Detection**: Days-to-stockout, deficit volume, and financial impact scoring.
* **Prescriptive Mitigation Engine**: Evaluates 7 action levers with Google OR-Tools MILP optimization.
* **Planner Approval Workbench**: 4-way trade-off analysis with transactional decision persistence.
* **Integrity Engine**: Anomaly detection across 12 data quality categories.
* **Immutable Audit Ledger**: End-to-end governance and traceability.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception Handlers
app.add_exception_handler(SupplyChainIQException, domain_exception_handler)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Structured handler for FastAPI request schema validation errors."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": {
                "code": "REQUEST_VALIDATION_ERROR",
                "message": "Invalid request parameters or payload structure.",
                "details": exc.errors(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "path": request.url.path,
            },
        },
    )


# Include API v1 Router
app.include_router(api_v1_router, prefix="/api")


@app.get("/health", tags=["Health & Diagnostics"])
async def health_check():
    """System health check and database connectivity diagnostic."""
    return {
        "status": "HEALTHY",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "api_version": "v1",
        "docs_url": "/docs",
    }


@app.get("/", tags=["Root"])
async def root():
    """Root entrypoint redirecting to OpenAPI documentation."""
    return {
        "message": f"Welcome to {settings.APP_NAME} API",
        "documentation": "/docs",
        "redoc": "/redoc",
        "api_prefix": "/api/v1",
    }


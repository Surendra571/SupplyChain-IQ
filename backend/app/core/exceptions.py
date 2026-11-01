"""SupplyChain IQ - Structured Domain Exceptions & Error Envelopes."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from fastapi import Request
from fastapi.responses import JSONResponse


class SupplyChainIQException(Exception):
    """Base exception for all domain and service errors."""
    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_SERVER_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class EntityNotFoundError(SupplyChainIQException):
    def __init__(self, entity_name: str, identifier: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"{entity_name} with identifier '{identifier}' was not found.",
            code="ENTITY_NOT_FOUND",
            status_code=404,
            details=details or {"entity": entity_name, "identifier": identifier},
        )


class UnauthorizedError(SupplyChainIQException):
    def __init__(self, message: str = "Authentication credentials required."):
        super().__init__(
            message=message,
            code="UNAUTHORIZED",
            status_code=401,
        )


class ForbiddenError(SupplyChainIQException):
    def __init__(self, message: str = "You do not have permission to execute this operation."):
        super().__init__(
            message=message,
            code="FORBIDDEN_OPERATION",
            status_code=403,
        )


class BusinessRuleViolationError(SupplyChainIQException):
    def __init__(self, message: str, code: str = "BUSINESS_RULE_VIOLATION", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code=code,
            status_code=422,
            details=details,
        )


class ConflictError(SupplyChainIQException):
    def __init__(self, message: str, code: str = "RESOURCE_CONFLICT", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code=code,
            status_code=409,
            details=details,
        )


class IdempotencyConflictError(ConflictError):
    def __init__(self, key: str):
        super().__init__(
            message=f"An operation with Idempotency-Key '{key}' is already in progress.",
            code="IDEMPOTENCY_IN_PROGRESS",
            details={"idempotency_key": key},
        )


async def domain_exception_handler(request: Request, exc: SupplyChainIQException) -> JSONResponse:
    """FastAPI exception handler for SupplyChainIQException domain hierarchy."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "path": request.url.path,
            },
        },
    )


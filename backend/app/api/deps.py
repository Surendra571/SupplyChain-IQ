"""SupplyChain IQ - FastAPI Route Dependencies."""

from typing import Annotated, AsyncGenerator, List, Optional
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import AsyncSessionLocal
from backend.app.core.exceptions import ForbiddenError, UnauthorizedError
from backend.app.core.rbac import Permission, UserRole, has_permission
from backend.app.core.security import STANDARD_USERS, decode_access_token

security = HTTPBearer(auto_error=False)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency injecting an async SQLAlchemy session."""
    if AsyncSessionLocal is None:
        raise RuntimeError("Async database sessionmaker not configured.")
    async with AsyncSessionLocal() as session:
        yield session


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """Dependency validating the Bearer JWT token and returning the user claims."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    email = payload.get("sub")
    role_str = payload.get("role")
    name = payload.get("name")

    if not email or not role_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token claims.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_role = UserRole(role_str)
    except ValueError:
        user_role = UserRole.PLANNER

    return {
        "user_id": payload.get("user_id", email),
        "email": email,
        "full_name": name or email,
        "role": user_role,
    }


def require_roles(allowed_roles: List[UserRole]):
    """Enforce that the authenticated user has one of the required roles."""
    async def role_checker(current_user: Annotated[dict, Depends(get_current_user)]):
        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user['role'].value}' lacks permission for this endpoint.",
            )
        return current_user
    return role_checker


def require_permission_dep(permission: Permission):
    """Enforce that the authenticated user possesses a specific permission."""
    async def perm_checker(current_user: Annotated[dict, Depends(get_current_user)]):
        if not has_permission(current_user["role"], permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User role '{current_user['role'].value}' lacks required permission '{permission.value}'.",
            )
        return current_user
    return perm_checker


def get_idempotency_key(
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key", description="Unique client UUID preventing duplicate execution"),
) -> Optional[str]:
    return idempotency_key


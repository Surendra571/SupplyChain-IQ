"""SupplyChain IQ - Authentication Router."""

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.api.deps import get_current_user
from backend.app.core.rbac import ROLE_PERMISSIONS, UserRole
from backend.app.core.security import STANDARD_USERS, create_access_token, verify_password
from backend.app.schemas.auth import LoginRequest, TokenResponse, UserProfile

router = APIRouter(prefix="/auth", tags=["Authentication & Access"])


@router.post("/login", response_model=TokenResponse, summary="User Login & JWT Generation")
async def login(credentials: LoginRequest):
    """Authenticate with enterprise credentials and receive a signed JWT bearer token."""
    user = STANDARD_USERS.get(credentials.email)
    if not user or not verify_password(credentials.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(
        subject=user["email"],
        role=user["role"],
        full_name=user["full_name"],
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        role=user["role"],
        user_id=user["user_id"],
        email=user["email"],
        full_name=user["full_name"],
    )


@router.get("/me", response_model=UserProfile, summary="Current Authenticated User Profile")
async def get_me(current_user: Annotated[dict, Depends(get_current_user)]):
    """Retrieve identity and authorized role permissions of current user."""
    role: UserRole = current_user["role"]
    perms = [p.value for p in ROLE_PERMISSIONS.get(role, set())]
    return UserProfile(
        user_id=current_user["user_id"],
        email=current_user["email"],
        full_name=current_user["full_name"],
        role=role,
        permissions=perms,
    )


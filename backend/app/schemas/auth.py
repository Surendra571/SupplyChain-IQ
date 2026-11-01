"""SupplyChain IQ - Authentication & Authorization Schemas."""

from typing import List
from pydantic import BaseModel, EmailStr, Field
from backend.app.core.rbac import UserRole


class LoginRequest(BaseModel):
    """User login credential payload."""
    email: EmailStr = Field(..., description="Enterprise work email")
    password: str = Field(..., min_length=6, description="Plaintext password")


class TokenResponse(BaseModel):
    """Signed JWT authorization response."""
    access_token: str
    token_type: str = "bearer"
    role: UserRole
    user_id: str
    email: str
    full_name: str


class UserProfile(BaseModel):
    """Authenticated user persona profile with resolved permissions."""
    user_id: str
    email: str
    full_name: str
    role: UserRole
    permissions: List[str]


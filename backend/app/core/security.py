"""SupplyChain IQ - Security, Password Hashing & JWT Token Management."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import bcrypt
import jwt

from backend.app.core.config import settings
from backend.app.core.rbac import UserRole


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(
    subject: str,
    role: UserRole,
    full_name: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Generate a signed JWT bearer token."""
    expire = datetime.now(timezone.utc) + (
        expires_delta if expires_delta else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {
        "sub": subject,
        "role": role.value if isinstance(role, UserRole) else role,
        "name": full_name,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "iss": "SupplyChain-IQ-Auth",
    }
    encoded_jwt = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate a signed JWT token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.PyJWTError as e:
        raise ValueError(f"Invalid or expired JWT token: {e}") from e


# Demo / Standard Seed Accounts for Enterprise Personas
STANDARD_USERS: Dict[str, Dict[str, Any]] = {
    "planner@supplychainiq.com": {
        "user_id": "USR-PLAN-01",
        "email": "planner@supplychainiq.com",
        "full_name": "Elena Rostova",
        "role": UserRole.PLANNER,
        "hashed_password": hash_password("Planner123!"),
        "is_active": True,
    },
    "procurement@supplychainiq.com": {
        "user_id": "USR-PROC-01",
        "email": "procurement@supplychainiq.com",
        "full_name": "David Sterling",
        "role": UserRole.PROCUREMENT_MANAGER,
        "hashed_password": hash_password("Procure123!"),
        "is_active": True,
    },
    "logistics@supplychainiq.com": {
        "user_id": "USR-LOG-01",
        "email": "logistics@supplychainiq.com",
        "full_name": "Marcus Vance",
        "role": UserRole.LOGISTICS_ANALYST,
        "hashed_password": hash_password("Logistics123!"),
        "is_active": True,
    },
    "warehouse@supplychainiq.com": {
        "user_id": "USR-WH-01",
        "email": "warehouse@supplychainiq.com",
        "full_name": "Clara Jensen",
        "role": UserRole.WAREHOUSE_OPERATOR,
        "hashed_password": hash_password("Warehouse123!"),
        "is_active": True,
    },
    "opsmanager@supplychainiq.com": {
        "user_id": "USR-OPS-01",
        "email": "opsmanager@supplychainiq.com",
        "full_name": "Arthur Pendelton",
        "role": UserRole.OPERATIONS_MANAGER,
        "hashed_password": hash_password("OpsMgr123!"),
        "is_active": True,
    },
    "admin@supplychainiq.com": {
        "user_id": "USR-ADMIN-01",
        "email": "admin@supplychainiq.com",
        "full_name": "System Administrator",
        "role": UserRole.ADMINISTRATOR,
        "hashed_password": hash_password("Admin123!"),
        "is_active": True,
    },
}


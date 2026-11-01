"""SupplyChain IQ - Role-Based Access Control (RBAC) & Permissions."""

from enum import Enum
from typing import List, Set


class UserRole(str, Enum):
    """Business personas and access tiers defined for SupplyChain IQ."""
    PLANNER = "Planner"
    PROCUREMENT_MANAGER = "Procurement Manager"
    LOGISTICS_ANALYST = "Logistics Analyst"
    WAREHOUSE_OPERATOR = "Warehouse Operator"
    OPERATIONS_MANAGER = "Operations Manager"
    ADMINISTRATOR = "Administrator"


class Permission(str, Enum):
    """Granular operational permissions."""
    PLANNING_RUN_TRIGGER = "planning:run_trigger"
    PLANNING_RUN_VIEW = "planning:run_view"
    SHORTAGE_VIEW = "shortage:view"
    SHORTAGE_ACKNOWLEDGE = "shortage:acknowledge"
    MITIGATION_VIEW = "mitigation:view"
    MITIGATION_APPROVE = "mitigation:approve"
    MITIGATION_REJECT = "mitigation:reject"
    MITIGATION_OVERRIDE = "mitigation:override"
    DATA_QUALITY_SCAN = "data_quality:scan"
    DATA_QUALITY_VIEW = "data_quality:view"
    AUDIT_VIEW = "audit:view"
    MASTER_DATA_VIEW = "master_data:view"
    ADMIN_MANAGE = "admin:manage"


# Role-to-Permissions Mapping matrix
ROLE_PERMISSIONS: dict[UserRole, Set[Permission]] = {
    UserRole.ADMINISTRATOR: set(Permission),  # Full access

    UserRole.OPERATIONS_MANAGER: {
        Permission.PLANNING_RUN_TRIGGER,
        Permission.PLANNING_RUN_VIEW,
        Permission.SHORTAGE_VIEW,
        Permission.SHORTAGE_ACKNOWLEDGE,
        Permission.MITIGATION_VIEW,
        Permission.MITIGATION_APPROVE,
        Permission.MITIGATION_REJECT,
        Permission.MITIGATION_OVERRIDE,
        Permission.DATA_QUALITY_SCAN,
        Permission.DATA_QUALITY_VIEW,
        Permission.AUDIT_VIEW,
        Permission.MASTER_DATA_VIEW,
    },

    UserRole.PLANNER: {
        Permission.PLANNING_RUN_TRIGGER,
        Permission.PLANNING_RUN_VIEW,
        Permission.SHORTAGE_VIEW,
        Permission.SHORTAGE_ACKNOWLEDGE,
        Permission.MITIGATION_VIEW,
        Permission.MITIGATION_APPROVE,
        Permission.MITIGATION_REJECT,
        Permission.MITIGATION_OVERRIDE,
        Permission.DATA_QUALITY_VIEW,
        Permission.AUDIT_VIEW,
        Permission.MASTER_DATA_VIEW,
    },

    UserRole.PROCUREMENT_MANAGER: {
        Permission.PLANNING_RUN_VIEW,
        Permission.SHORTAGE_VIEW,
        Permission.MITIGATION_VIEW,
        Permission.MITIGATION_APPROVE,
        Permission.MITIGATION_REJECT,
        Permission.MASTER_DATA_VIEW,
    },

    UserRole.LOGISTICS_ANALYST: {
        Permission.PLANNING_RUN_VIEW,
        Permission.SHORTAGE_VIEW,
        Permission.MITIGATION_VIEW,
        Permission.MASTER_DATA_VIEW,
    },

    UserRole.WAREHOUSE_OPERATOR: {
        Permission.PLANNING_RUN_VIEW,
        Permission.SHORTAGE_VIEW,
        Permission.MASTER_DATA_VIEW,
    },
}


def has_permission(user_role: UserRole, permission: Permission) -> bool:
    """Check if a specific role possesses the requested permission."""
    allowed = ROLE_PERMISSIONS.get(user_role, set())
    return permission in allowed


# app/schemas/__init__.py
"""
Pydantic Schemas for Municipality ERP API
=========================================
"""

from .budget import (
    BudgetStatus,
    TransactionStatus,
    BlockFundsRequest,
    ReleaseFundsRequest,
    ConfirmSpendRequest,
    BudgetCheckResponse,
    BudgetTransactionResponse,
    BudgetListResponse,
    InsufficientFundsResponse,
    BudgetNotFoundResponse,
)

# Legacy schemas from the old app/schemas.py
from .legacy import (
    OrgHint,
    ActionHint,
    ExternalSpecialActionPayload,
    SpecialActionResponse,
    UserContextSchema,
    SubsystemInfoSchema,
    ActivityConstraintSchema,
    AllowedActivitySchema,
    DashboardInitResponse,
)

# RBAC schemas for access control
from .rbac import (
    SubsystemAccessAssignRequest,
    SubsystemAccessAssignByCodeRequest,
    SubsystemInfoResponse,
    UserSubsystemAccessResponse,
    AllowedSubsystemsResponse,
    AccessUpdateResponse,
)

__all__ = [
    # Budget schemas
    "BudgetStatus",
    "TransactionStatus",
    "BlockFundsRequest",
    "ReleaseFundsRequest",
    "ConfirmSpendRequest",
    "BudgetCheckResponse",
    "BudgetTransactionResponse",
    "BudgetListResponse",
    "InsufficientFundsResponse",
    "BudgetNotFoundResponse",
    # Legacy schemas
    "OrgHint",
    "ActionHint",
    "ExternalSpecialActionPayload",
    "SpecialActionResponse",
    "UserContextSchema",
    "SubsystemInfoSchema",
    "ActivityConstraintSchema",
    "AllowedActivitySchema",
    "DashboardInitResponse",
    # RBAC schemas
    "SubsystemAccessAssignRequest",
    "SubsystemAccessAssignByCodeRequest",
    "SubsystemInfoResponse",
    "UserSubsystemAccessResponse",
    "AllowedSubsystemsResponse",
    "AccessUpdateResponse",
]

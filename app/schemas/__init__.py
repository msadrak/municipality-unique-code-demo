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

# Credit Request schemas (Stage 1 Gateway)
from .credit_request import (
    CreditRequestCreate,
    CreditRequestApprove,
    CreditRequestReject,
    CreditRequestCancel,
    CreditRequestResponse,
    CreditRequestListItem,
    CreditRequestListResponse,
    CreditRequestActionResponse,
    CreditRequestLogEntry,
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

# Contractor schemas (Phase 2)
from .contractor import (
    ContractorCreate,
    ContractorSetadFetch,
    ContractorResponse,
    ContractorListItem,
    ContractorListResponse,
    SetadContractorInfo,
    SetadSearchResponse,
)

# Contract Template schemas (Phase 2)
from .contract_template import (
    ContractTemplateCreate,
    ContractTemplateUpdate,
    ContractTemplateResponse,
    ContractTemplateListItem,
    ContractTemplateListResponse,
)

# Contract Lifecycle schemas (Sprint 2)
from .contract import (
    ContractDraftCreate,
    ContractResponse,
    ContractListItem,
    ContractListResponse,
    ContractRenderResponse,
    ContractStatusTransition,
)

# Progress Statement schemas (Sprint 3)
from .statement import (
    StatementCreate,
    StatementApprove,
    StatementResponse,
    StatementListItem,
    StatementListResponse,
    StatementFinancialSummary,
)

# HR Funding Request schemas
from .funding_workflow import (
    FundingRequestCreate,
    FundingRequestUpdate,
    FundingRequestResponse,
    AdvanceRequest,
    FundingWorkflowLogResponse,
)
from .attendance import (
    AttendanceAggregationItem,
    AttendanceAggregationOut,
    AttendanceSheetRejectRequest,
    AttendanceReconciliationOut,
    AttendanceRecordOut,
    AttendanceSheetOut,
    PenaltyRecordCreate,
    PenaltyRecordOut,
    SheetMetaSummary,
    WorkPeriodApprovalOut,
    WorkPeriodStatusOut,
    WorkflowStatusLabel,
    WorkflowTransitionRequest,
)
from .notification import NotificationOut
from .civil import CivilProjectListItem
from .finance import (
    FinancialMatrixCreate,
    FinancialMatrixOut,
    FinancialMatrixUpdate,
    FinancialMatrixYektaCodeOut,
    FinancialMatrixYektaCodeRequest,
)
from .hr_finance import (
    GeneratedHRTransactionCodeOut,
    HRFinanceAllocationLineIn,
    HRFinanceAllocationLineOut,
    HRFinanceDateRangeOut,
    HRFinanceFinalizeRequest,
    HRFinanceFinancialRulesOut,
    HRFinanceOperationalContextOut,
    HRFinanceTransactionInfoOut,
    HRFinanceWorkflowContextOut,
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
    # Credit Request schemas
    "CreditRequestCreate",
    "CreditRequestApprove",
    "CreditRequestReject",
    "CreditRequestCancel",
    "CreditRequestResponse",
    "CreditRequestListItem",
    "CreditRequestListResponse",
    "CreditRequestActionResponse",
    "CreditRequestLogEntry",
    # RBAC schemas
    "SubsystemAccessAssignRequest",
    "SubsystemAccessAssignByCodeRequest",
    "SubsystemInfoResponse",
    "UserSubsystemAccessResponse",
    "AllowedSubsystemsResponse",
    "AccessUpdateResponse",
    # Contractor schemas (Phase 2)
    "ContractorCreate",
    "ContractorSetadFetch",
    "ContractorResponse",
    "ContractorListItem",
    "ContractorListResponse",
    "SetadContractorInfo",
    "SetadSearchResponse",
    # Contract Template schemas (Phase 2)
    "ContractTemplateCreate",
    "ContractTemplateUpdate",
    "ContractTemplateResponse",
    "ContractTemplateListItem",
    "ContractTemplateListResponse",
    # Contract Lifecycle schemas (Sprint 2)
    "ContractDraftCreate",
    "ContractResponse",
    "ContractListItem",
    "ContractListResponse",
    "ContractRenderResponse",
    "ContractStatusTransition",
    # Progress Statement schemas (Sprint 3)
    "StatementCreate",
    "StatementApprove",
    "StatementResponse",
    "StatementListItem",
    "StatementListResponse",
    "StatementFinancialSummary",
    # HR Funding Request schemas
    "FundingRequestCreate",
    "FundingRequestUpdate",
    "FundingRequestResponse",
    "AdvanceRequest",
    "FundingWorkflowLogResponse",
    "AttendanceAggregationItem",
    "AttendanceAggregationOut",
    "AttendanceSheetRejectRequest",
    "AttendanceReconciliationOut",
    "AttendanceRecordOut",
    "AttendanceSheetOut",
    "GeneratedHRTransactionCodeOut",
    "HRFinanceAllocationLineIn",
    "HRFinanceAllocationLineOut",
    "HRFinanceDateRangeOut",
    "HRFinanceFinalizeRequest",
    "HRFinanceFinancialRulesOut",
    "HRFinanceOperationalContextOut",
    "HRFinanceTransactionInfoOut",
    "HRFinanceWorkflowContextOut",
    "NotificationOut",
    "CivilProjectListItem",
    "FinancialMatrixCreate",
    "FinancialMatrixOut",
    "FinancialMatrixUpdate",
    "FinancialMatrixYektaCodeOut",
    "FinancialMatrixYektaCodeRequest",
    "PenaltyRecordCreate",
    "PenaltyRecordOut",
    "SheetMetaSummary",
    "WorkPeriodApprovalOut",
    "WorkPeriodStatusOut",
    "WorkflowStatusLabel",
    "WorkflowTransitionRequest",
]


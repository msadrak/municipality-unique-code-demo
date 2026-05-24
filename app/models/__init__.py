"""
Compatibility package for SQLAlchemy models.

The codebase historically stored all models in ``app/models.py``.
This package preserves the existing ``app.models`` import surface while
allowing new model submodules such as ``app.models.attendance``.
"""
from __future__ import annotations

import importlib.util as _importlib_util
import sys as _sys
from pathlib import Path as _Path

_LEGACY_MODULE_NAME = "app._legacy_models"
_LEGACY_PATH = _Path(__file__).resolve().parent.parent / "models.py"

_spec = _importlib_util.spec_from_file_location(_LEGACY_MODULE_NAME, _LEGACY_PATH)
if _spec is None or _spec.loader is None:
    raise ImportError(f"Cannot load legacy models module from {_LEGACY_PATH}")

_legacy_module = _sys.modules.get(_LEGACY_MODULE_NAME)
if _legacy_module is None:
    _legacy_module = _importlib_util.module_from_spec(_spec)
    _sys.modules[_LEGACY_MODULE_NAME] = _legacy_module
    _spec.loader.exec_module(_legacy_module)

for _name in dir(_legacy_module):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_legacy_module, _name)

from .enums import AttendanceSheetStatus, UserRole, WorkFlowStatus
from .users import Notification, User
from .attendance import (
    Attachment,
    AttendanceRecord,
    ContractorStatement,
    ContractorStatementItem,
    PenaltyRecord,
    RegionalAttendanceSheet,
    WorkPeriod,
)
from .organization import Activity, OrgUnit, OrgUnitType
from .finance import FinancialMatrix, TransactionAllocation, generate_financial_matrix_yekta_code
from .finance_rules import FinancialRule
from .civil import (
    ApprovalTask,
    ApprovalTaskStatus,
    CivilProject,
    CivilProjectAssignment,
    CivilProjectRole,
    DOCUMENT_PAYLOAD_REQUIREMENTS,
    EntityDocument,
    StepAction,
    WorkflowStep,
    WorkflowStepDefinition,
    WorkflowTransition,
    validate_document_payload,
)

__all__ = sorted(name for name in globals() if not name.startswith("_"))

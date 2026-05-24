from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.models.enums import AttendanceSheetStatus, WorkFlowStatus


# ---------------------------------------------------------------------------
# WorkFlowStatus Pydantic mirror (for responses / docs)
# ---------------------------------------------------------------------------


class WorkFlowStatusSchema(str, Enum):
    """Pydantic-side mirror of the SQLAlchemy WorkFlowStatus enum."""

    DRAFT_REGIONS = "DRAFT_REGIONS"
    PENDING_SECURITY_AGGREGATION = "PENDING_SECURITY_AGGREGATION"
    PENDING_CONTRACTOR_STATEMENT = "PENDING_CONTRACTOR_STATEMENT"
    PENDING_SECURITY_AUDIT = "PENDING_SECURITY_AUDIT"
    FINAL_APPROVED = "FINAL_APPROVED"
    PENDING_UNIQUE_CODE = "PENDING_UNIQUE_CODE"
    SENT_TO_FINANCE = "SENT_TO_FINANCE"


# ---------------------------------------------------------------------------
# WorkPeriod schemas
# ---------------------------------------------------------------------------


class WorkPeriodCreate(BaseModel):
    """Payload to create or get-or-create a WorkPeriod for a given month."""

    year: int
    month: int


class WorkPeriodUpdate(BaseModel):
    """Fields that may be updated on a WorkPeriod (status transitions, etc.)."""

    status: Optional[WorkFlowStatusSchema] = None
    total_regions_uploaded: Optional[int] = None


class WorkPeriodOut(BaseModel):
    """Full read representation of a WorkPeriod."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    year: int
    month: int
    status: WorkFlowStatusSchema
    total_regions_uploaded: int
    created_at: datetime
    updated_at: Optional[datetime] = None


class WorkPeriodStatusOut(BaseModel):
    status: WorkFlowStatusSchema
    total_uploaded: int
    uploaded_regions: list[str]
    missing_regions: list[str]


class WorkPeriodApprovalOut(BaseModel):
    success: bool
    status: WorkFlowStatusSchema
    message: str
    financial_transaction_id: Optional[int] = None
    financial_transaction_status: Optional[str] = None
    financial_tracking_number: Optional[str] = None


# ---------------------------------------------------------------------------
# Penalty Record schemas
# ---------------------------------------------------------------------------


class PenaltyRecordCreate(BaseModel):
    description: str
    count: int = Field(gt=0)
    unit_amount: Decimal = Field(gt=0)


class PenaltyRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    work_period_id: int
    description: str
    count: int
    unit_amount: Decimal
    total_amount: Decimal


# ---------------------------------------------------------------------------
# Attendance Record schemas
# ---------------------------------------------------------------------------


class AttendanceRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sheet_id: int
    row_number: int
    work_period_id: Optional[int] = None
    location: Optional[str] = None
    full_name: str
    father_name: Optional[str] = None
    national_id: Optional[str] = None
    marital_status: Optional[str] = None
    children_count: Optional[int] = None
    start_date: Optional[str] = None
    average_per_capita: Optional[Decimal] = None
    min_paid_hours: Optional[Decimal] = None
    max_paid_hours: Optional[Decimal] = None
    monthly_performance_days: Optional[Decimal] = None
    monthly_absence_days: Optional[Decimal] = None
    overtime_replacement: Optional[Decimal] = None
    overtime_hours: Optional[Decimal] = None
    total_average_per_capita: Optional[Decimal] = None
    total_overtime_given: Optional[Decimal] = None
    performance_balance: Optional[str] = None


class AttendanceRecordUpdate(BaseModel):
    location: Optional[str] = None
    full_name: Optional[str] = None
    father_name: Optional[str] = None
    national_id: Optional[str] = None
    marital_status: Optional[str] = None
    children_count: Optional[int] = None
    start_date: Optional[str] = None
    average_per_capita: Optional[Decimal] = None
    min_paid_hours: Optional[Decimal] = None
    max_paid_hours: Optional[Decimal] = None
    monthly_performance_days: Optional[Decimal] = None
    monthly_absence_days: Optional[Decimal] = None
    overtime_replacement: Optional[Decimal] = None
    overtime_hours: Optional[Decimal] = None
    total_average_per_capita: Optional[Decimal] = None
    total_overtime_given: Optional[Decimal] = None
    performance_balance: Optional[str] = None


class AttendanceAuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    record_id: int
    changed_by_user_id: Optional[int] = None
    field_name: str
    old_value: str
    new_value: str
    created_at: datetime
    changed_by_full_name: Optional[str] = None


# ---------------------------------------------------------------------------
# Attendance Sheet schemas
# ---------------------------------------------------------------------------


class AttachmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sheet_id: int
    file_path: str
    file_name: str
    file_type: str
    created_at: datetime


class AttendanceSheetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    year: Optional[int] = None
    month: Optional[int] = None
    region: Optional[str] = None
    work_period_id: Optional[int] = None
    original_filename: str
    row_count: int
    status: AttendanceSheetStatus
    rejection_reason: Optional[str] = None
    created_at: datetime
    records: list[AttendanceRecordOut] = []
    attachments: list[AttachmentOut] = []


# ---------------------------------------------------------------------------
# Workflow transition (existing)
# ---------------------------------------------------------------------------


class WorkflowTransitionRequest(BaseModel):
    action: str
    rejection_reason: Optional[str] = None


class AttendanceSheetRejectRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class WorkflowStatusLabel(str, Enum):
    DRAFT = "پیش‌نویس"
    CREATOR_APPROVED = "تأیید ثبت‌کننده"
    COMPANY_REP_APPROVED = "تأیید نماینده شرکت"
    SECURITY_APPROVED = "تأیید حراست"
    GM_APPROVED = "تأیید نهایی"
    NEEDS_CORRECTION = "نیازمند اصلاح"
    REJECTED = "رد شده"


# ---------------------------------------------------------------------------
# Aggregation & formatting helpers
# ---------------------------------------------------------------------------


_PERSIAN_NUMBER_MAP = str.maketrans(
    "0123456789,.",
    "۰۱۲۳۴۵۶۷۸۹٬٫",
)


def _to_persian_number(value: str) -> str:
    return value.translate(_PERSIAN_NUMBER_MAP)


class SheetMetaSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sheet_id: int
    title: str
    year: Optional[int] = None
    month: Optional[int] = None
    region_name: Optional[str] = None
    original_filename: str
    row_count: int
    created_at: datetime
    creator_approved_at: Optional[datetime] = None
    company_rep_approved_at: Optional[datetime] = None
    security_approved_at: Optional[datetime] = None
    gm_approved_at: Optional[datetime] = None


class AttendanceAggregationItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sheet: SheetMetaSummary
    workflow_status: str
    workflow_status_label: str
    total_personnel: int
    total_worked_hours: float
    total_amount: int

    @computed_field
    @property
    def total_amount_formatted(self) -> str:
        formatted_amount = _to_persian_number(f"{self.total_amount:,}")
        return f"{formatted_amount} ریال"


class AttendanceAggregationOut(BaseModel):
    count: int
    items: list[AttendanceAggregationItem]


class AttendanceReconciliationOut(BaseModel):
    year: int
    month: int
    status: WorkFlowStatusSchema
    region_total: Decimal
    contractor_total: Decimal
    total_penalties_amount: Decimal
    final_payable_amount: Decimal
    financial_transaction_id: Optional[int] = None
    financial_transaction_status: Optional[str] = None
    financial_tracking_number: Optional[str] = None
    financial_unique_code: Optional[str] = None
    penalties: list[PenaltyRecordOut]

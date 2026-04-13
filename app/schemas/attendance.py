from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, computed_field

from app.models.enums import AttendanceSheetStatus


class AttendanceRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    row_number: int
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


class AttendanceSheetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    year: Optional[int] = None
    month: Optional[int] = None
    region: Optional[str] = None
    original_filename: str
    row_count: int
    status: AttendanceSheetStatus
    created_at: datetime
    records: list[AttendanceRecordOut] = []


class WorkflowTransitionRequest(BaseModel):
    action: str
    rejection_reason: Optional[str] = None


class WorkflowStatusLabel(str, Enum):
    DRAFT = "پیش‌نویس"
    CREATOR_APPROVED = "تأیید ثبت‌کننده"
    COMPANY_REP_APPROVED = "تأیید نماینده شرکت"
    SECURITY_APPROVED = "تأیید حراست"
    GM_APPROVED = "تأیید نهایی"
    NEEDS_CORRECTION = "نیازمند اصلاح"
    REJECTED = "رد شده"


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
    region_name: str
    region_total: Decimal
    contractor_total: Decimal
    difference: Decimal
    is_matched: bool

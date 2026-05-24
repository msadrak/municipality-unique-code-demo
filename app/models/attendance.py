from sqlalchemy import (
    Column,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.enums import AttendanceSheetStatus, WorkFlowStatus


# ---------------------------------------------------------------------------
# WorkPeriod — central spine for the monthly 4-stage workflow
# ---------------------------------------------------------------------------


class WorkPeriod(Base):
    """
    One definitive workflow instance per calendar month.

    Lifecycle:
        DRAFT_REGIONS → PENDING_SECURITY_AGGREGATION
        → PENDING_CONTRACTOR_STATEMENT → PENDING_SECURITY_AUDIT
        → FINAL_APPROVED
    """

    __tablename__ = "work_periods"
    __table_args__ = (
        UniqueConstraint("year", "month", name="uq_work_period_year_month"),
    )

    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    status = Column(
        SAEnum(WorkFlowStatus, name="work_flow_status"),
        default=WorkFlowStatus.DRAFT_REGIONS,
        nullable=False,
    )
    total_regions_uploaded = Column(Integer, default=0, nullable=False)
    financial_unique_code = Column(String(64), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # -- children --
    sheets = relationship(
        "RegionalAttendanceSheet",
        back_populates="work_period",
        cascade="all, delete-orphan",
    )
    contractor_statements = relationship(
        "ContractorStatement",
        back_populates="work_period",
        cascade="all, delete-orphan",
    )
    penalty_records = relationship(
        "PenaltyRecord",
        back_populates="work_period",
        cascade="all, delete-orphan",
    )


# ---------------------------------------------------------------------------
# RegionalAttendanceSheet — 18-column regional data (Stage 1)
# ---------------------------------------------------------------------------


class RegionalAttendanceSheet(Base):
    __tablename__ = "regional_attendance_sheets"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    year = Column(Integer, nullable=True)
    month = Column(Integer, nullable=True)
    region = Column(String(128), nullable=True)
    original_filename = Column(String(512), nullable=False)
    row_count = Column(Integer, nullable=False, default=0)
    status = Column(
        SAEnum(AttendanceSheetStatus, name="attendance_sheet_status"),
        default=AttendanceSheetStatus.DRAFT,
        nullable=False,
    )

    # -- FK to WorkPeriod --
    work_period_id = Column(
        Integer,
        ForeignKey("work_periods.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    company_rep_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    security_supervisor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    gm_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    creator_approved_at = Column(DateTime(timezone=True), nullable=True)
    company_rep_approved_at = Column(DateTime(timezone=True), nullable=True)
    security_approved_at = Column(DateTime(timezone=True), nullable=True)
    gm_approved_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    declared_total_amount = Column(Numeric(18, 2), nullable=True)

    # -- relationships --
    work_period = relationship("WorkPeriod", back_populates="sheets")
    records = relationship(
        "AttendanceRecord",
        back_populates="sheet",
        cascade="all, delete-orphan",
    )
    contractor_statements = relationship(
        "ContractorStatement",
        back_populates="sheet",
        cascade="all, delete-orphan",
    )
    attachments = relationship(
        "Attachment",
        back_populates="sheet",
        cascade="all, delete-orphan",
    )


# ---------------------------------------------------------------------------
# AttendanceRecord — individual personnel rows within a sheet
# ---------------------------------------------------------------------------


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id = Column(Integer, primary_key=True, index=True)
    sheet_id = Column(
        Integer,
        ForeignKey("regional_attendance_sheets.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Direct FK to WorkPeriod for efficient querying across all regions
    work_period_id = Column(
        Integer,
        ForeignKey("work_periods.id", ondelete="SET NULL"),
        nullable=True,
    )
    row_number = Column(Integer, nullable=False)
    location = Column(String(255), nullable=True)
    full_name = Column(String(255), nullable=False)
    father_name = Column(String(255), nullable=True)
    national_id = Column(String(32), nullable=True)
    marital_status = Column(String(64), nullable=True)
    children_count = Column(Integer, nullable=True)
    start_date = Column(String(64), nullable=True)
    average_per_capita = Column(Numeric(18, 2), nullable=True)
    min_paid_hours = Column(Numeric(12, 2), nullable=True)
    max_paid_hours = Column(Numeric(12, 2), nullable=True)
    monthly_performance_days = Column(Numeric(12, 2), nullable=True)
    monthly_absence_days = Column(Numeric(12, 2), nullable=True)
    overtime_replacement = Column(Numeric(12, 2), nullable=True)
    overtime_hours = Column(Numeric(12, 2), nullable=True)
    total_average_per_capita = Column(Numeric(18, 2), nullable=True)
    total_overtime_given = Column(Numeric(18, 2), nullable=True)
    performance_balance = Column(Text, nullable=True)

    sheet = relationship("RegionalAttendanceSheet", back_populates="records")
    work_period = relationship("WorkPeriod")


# ---------------------------------------------------------------------------
# ContractorStatement — 6-column company invoice (Stage 3)
# ---------------------------------------------------------------------------


class ContractorStatement(Base):
    __tablename__ = "contractor_statements"

    id = Column(Integer, primary_key=True, index=True)
    sheet_id = Column(
        Integer,
        ForeignKey("regional_attendance_sheets.id", ondelete="SET NULL"),
        nullable=True,
    )
    # FK to WorkPeriod — the invoice belongs to a specific month
    work_period_id = Column(
        Integer,
        ForeignKey("work_periods.id", ondelete="SET NULL"),
        nullable=True,
    )
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    region_name = Column(String(128), nullable=False)
    declared_total_amount = Column(Numeric(18, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    sheet = relationship("RegionalAttendanceSheet", back_populates="contractor_statements")
    work_period = relationship("WorkPeriod", back_populates="contractor_statements")
    items = relationship(
        "ContractorStatementItem",
        back_populates="statement",
        cascade="all, delete-orphan",
    )


# ---------------------------------------------------------------------------
# ContractorStatementItem — line-items within a contractor statement
# ---------------------------------------------------------------------------


class ContractorStatementItem(Base):
    __tablename__ = "contractor_statement_items"

    id = Column(Integer, primary_key=True, index=True)
    statement_id = Column(
        Integer,
        ForeignKey("contractor_statements.id", ondelete="CASCADE"),
        nullable=False,
    )
    sheet_id = Column(
        Integer,
        ForeignKey("regional_attendance_sheets.id", ondelete="CASCADE"),
        nullable=True,
    )
    row_number = Column(Integer, nullable=False)
    national_id = Column(String(32), nullable=True)
    full_name = Column(String(255), nullable=False)
    gross_amount = Column(Numeric(18, 2), nullable=True)
    tax_deduction = Column(Numeric(18, 2), nullable=True)
    insurance_deduction = Column(Numeric(18, 2), nullable=True)
    net_payable_amount = Column(Numeric(18, 2), nullable=True)

    statement = relationship("ContractorStatement", back_populates="items")
    sheet = relationship("RegionalAttendanceSheet")


# ---------------------------------------------------------------------------
# PenaltyRecord — applied contract deductions for a work period
# ---------------------------------------------------------------------------


class PenaltyRecord(Base):
    __tablename__ = "penalty_records"

    id = Column(Integer, primary_key=True, index=True)
    work_period_id = Column(
        Integer,
        ForeignKey("work_periods.id", ondelete="CASCADE"),
        nullable=False,
    )
    description = Column(String(255), nullable=False)
    count = Column(Integer, nullable=False)
    unit_amount = Column(Numeric(18, 2), nullable=False)
    total_amount = Column(Numeric(18, 2), nullable=False)

    work_period = relationship("WorkPeriod", back_populates="penalty_records")


# ---------------------------------------------------------------------------
# AttendanceAuditLog — tracks manual edits to attendance records
# ---------------------------------------------------------------------------


class AttendanceAuditLog(Base):
    __tablename__ = "attendance_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    record_id = Column(
        Integer,
        ForeignKey("attendance_records.id", ondelete="CASCADE"),
        nullable=False,
    )
    changed_by_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    field_name = Column(String(128), nullable=False)
    old_value = Column(String(255), nullable=True)
    new_value = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    record = relationship("AttendanceRecord", backref="audit_logs")
    changed_by_user = relationship("User")


# ---------------------------------------------------------------------------
# Attachment — PDF / image documents attached to a RegionalAttendanceSheet
# ---------------------------------------------------------------------------


class Attachment(Base):
    """
    Stores invoice / supporting document files (PDF or image) that a regional
    user uploads alongside the 18-column Excel attendance sheet.
    """

    __tablename__ = "sheet_attachments"

    id = Column(Integer, primary_key=True, index=True)
    sheet_id = Column(
        Integer,
        ForeignKey("regional_attendance_sheets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_path = Column(String(1024), nullable=False)   # relative path from project root
    file_name = Column(String(512), nullable=False)    # original filename shown to users
    file_type = Column(String(16), nullable=False)     # 'pdf' or 'image'
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # -- relationship --
    sheet = relationship("RegionalAttendanceSheet", back_populates="attachments")

from sqlalchemy import (
    Column,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.enums import AttendanceSheetStatus


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


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id = Column(Integer, primary_key=True, index=True)
    sheet_id = Column(
        Integer,
        ForeignKey("regional_attendance_sheets.id", ondelete="CASCADE"),
        nullable=False,
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


class ContractorStatement(Base):
    __tablename__ = "contractor_statements"

    id = Column(Integer, primary_key=True, index=True)
    sheet_id = Column(
        Integer,
        ForeignKey("regional_attendance_sheets.id", ondelete="SET NULL"),
        nullable=True,
    )
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    region_name = Column(String(128), nullable=False)
    declared_total_amount = Column(Numeric(18, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    sheet = relationship("RegionalAttendanceSheet", back_populates="contractor_statements")
    items = relationship(
        "ContractorStatementItem",
        back_populates="statement",
        cascade="all, delete-orphan",
    )


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

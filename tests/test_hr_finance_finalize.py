from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import (
    Activity,
    ContractorStatement,
    FinancialRule,
    OrgUnit,
    RegionalAttendanceSheet,
    Transaction,
    TransactionAllocation,
    User,
    WorkPeriod,
)
from app.models.enums import AttendanceSheetStatus, WorkFlowStatus
from app.routers.hr_finance import finalize_workflow_transaction, get_workflow_context
from app.schemas.hr_finance import HRFinanceFinalizeRequest


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def _seed_workflow_context(db_session):
    org_unit = OrgUnit(title="HR Finance Unit", code="01", org_type="UNIT")
    current_user = User(
        username="finance.user",
        hashed_password="hashed",
        full_name="Finance User",
        role="HR_ADMIN",
        is_active=True,
    )
    contractor_user = User(
        username="contractor.user",
        hashed_password="hashed",
        full_name="Sample Contractor",
        role="CONTRACTOR",
        is_active=True,
    )
    db_session.add_all([org_unit, current_user, contractor_user])
    db_session.flush()

    activity = Activity(
        name="تسویه کارکرد پیمانکاران",
        org_unit_id=org_unit.id,
        is_active=True,
    )
    db_session.add(activity)
    db_session.flush()

    financial_rule = FinancialRule(
        activity_id=activity.id,
        cost_center_code="CC-102",
        budget_line_code="BL-2020-8",
        financial_event_type="CONTRACTOR_PAYROLL",
        is_active=True,
    )
    work_period = WorkPeriod(
        year=1405,
        month=1,
        status=WorkFlowStatus.PENDING_UNIQUE_CODE,
        total_regions_uploaded=3,
    )
    db_session.add_all([financial_rule, work_period])
    db_session.flush()

    sheet = RegionalAttendanceSheet(
        title="Attendance Sheet",
        year=1405,
        month=1,
        region="منطقه 1",
        original_filename="attendance.xlsx",
        row_count=1,
        status=AttendanceSheetStatus.DRAFT,
        work_period_id=work_period.id,
        created_by_id=contractor_user.id,
    )
    db_session.add(sheet)
    db_session.flush()

    statement = ContractorStatement(
        sheet_id=sheet.id,
        work_period_id=work_period.id,
        year=1405,
        month=1,
        region_name="منطقه 1",
        declared_total_amount=Decimal("1000"),
    )
    transaction = Transaction(
        tracking_number="TRX-1405-TEST0001",
        unique_code=None,
        status="DRAFT",
        current_approval_level=0,
        created_by_id=current_user.id,
        zone_id=org_unit.id,
        activity_id=activity.id,
        amount=1000,
        beneficiary_name="Sample Contractor",
        contract_number="ATT-1405-01",
        description="HR finance test transaction",
        fiscal_year="1405",
        form_data={
            "attendance_work_period_id": work_period.id,
            "work_period_id": work_period.id,
            "year": 1405,
            "month": 1,
            "contractor_name": "Sample Contractor",
        },
    )
    db_session.add_all([statement, transaction])
    db_session.commit()

    return {
        "current_user": current_user,
        "transaction": transaction,
        "work_period": work_period,
    }


def test_finalize_hr_finance_transaction_persists_allocations(db_session):
    seeded = _seed_workflow_context(db_session)
    transaction = seeded["transaction"]
    current_user = seeded["current_user"]

    payload = HRFinanceFinalizeRequest(
        allocations=[
            {
                "org_unit_name": "منطقه 1",
                "cost_center_code": "CC-102",
                "budget_line_code": "BL-2020-8",
                "financial_event_type": "CONTRACTOR_PAYROLL",
                "allocated_amount": Decimal("600"),
                "legal_deductions": Decimal("50"),
                "penalties": Decimal("10"),
            },
            {
                "org_unit_name": "منطقه 3",
                "cost_center_code": "CC-204",
                "budget_line_code": "BL-2020-9",
                "financial_event_type": "CONTRACTOR_PAYROLL",
                "allocated_amount": Decimal("400"),
                "legal_deductions": Decimal("25"),
                "penalties": Decimal("5"),
            },
        ]
    )

    result = finalize_workflow_transaction(transaction.id, payload, db_session, current_user)

    assert len(result) == 2
    assert result[0].region == "منطقه 1"
    assert result[0].code.startswith("HR-140501-CC102-")
    assert result[1].code.startswith("HR-140501-CC204-")

    persisted_allocations = (
        db_session.query(TransactionAllocation)
        .filter(TransactionAllocation.transaction_id == transaction.id)
        .order_by(TransactionAllocation.id.asc())
        .all()
    )
    assert len(persisted_allocations) == 2
    assert persisted_allocations[0].unique_code == result[0].code
    assert persisted_allocations[1].net_amount == Decimal("370")

    refreshed_transaction = db_session.get(Transaction, transaction.id)
    refreshed_work_period = db_session.get(WorkPeriod, seeded["work_period"].id)

    assert refreshed_transaction.status == "SENT_TO_FINANCE"
    assert refreshed_transaction.unique_code == result[0].code
    assert refreshed_work_period.status == WorkFlowStatus.SENT_TO_FINANCE
    assert refreshed_work_period.financial_unique_code == result[0].code

    context = get_workflow_context(transaction.id, db_session, current_user)
    assert context["transaction"]["status"] == "SENT_TO_FINANCE"
    assert len(context["allocation_lines"]) == 2
    assert context["allocation_lines"][0]["unique_code"] == result[0].code


def test_finalize_hr_finance_transaction_rejects_unbalanced_allocations(db_session):
    seeded = _seed_workflow_context(db_session)
    transaction = seeded["transaction"]
    current_user = seeded["current_user"]

    payload = HRFinanceFinalizeRequest(
        allocations=[
            {
                "org_unit_name": "منطقه 1",
                "cost_center_code": "CC-102",
                "budget_line_code": "BL-2020-8",
                "financial_event_type": "CONTRACTOR_PAYROLL",
                "allocated_amount": Decimal("700"),
                "legal_deductions": Decimal("0"),
                "penalties": Decimal("0"),
            }
        ]
    )

    with pytest.raises(HTTPException) as exc_info:
        finalize_workflow_transaction(transaction.id, payload, db_session, current_user)

    assert exc_info.value.status_code == 400
    assert "sum of allocated amounts" in str(exc_info.value.detail).lower()
    assert db_session.query(TransactionAllocation).count() == 0

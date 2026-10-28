"""Seed rich contractor dashboard demo data for cleaning_contractor@test.com.

The script is intentionally scoped to volume-contract projects assigned to the
cleaning contractor demo user. Other contractors and non-volume projects are
left untouched.
"""
from __future__ import annotations

import re
import sys
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import inspect
from sqlalchemy.orm import Session

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.security import get_password_hash  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.models import (  # noqa: E402
    Activity,
    ApprovalTask,
    CivilProject,
    CivilProjectAssignment,
    CivilProjectRole,
    Contractor,
    EntityDocument,
    FinancialMatrix,
    OrgUnit,
    Transaction,
    User,
    UserRole,
    WorkflowStep,
    WorkflowStepDefinition,
)
from app.models.civil import ApprovalTaskStatus  # noqa: E402


CONTRACTOR_EMAIL = "cleaning_contractor@test.com"
CONTRACTOR_PASSWORD = "password123"
CONTRACTOR_NAME = "شرکت خدماتی نظافت"
CONTRACTOR_NATIONAL_ID = "14001234567"
CONTRACT_CATEGORY = "نظافت و پذیرایی"

STEP_FALLBACKS = {
    102: {
        "name": "تدقیق آنالیز حقوق - پیوست ۵",
        "role": UserRole.CONTRACTOR.value,
        "form_type": "APPENDIX_5_SALARY_ANALYSIS",
        "phase": 1,
    },
    103: {
        "name": "ارسال شده به بهادری",
        "role": UserRole.YEKTA_ADMIN.value,
        "form_type": "FINANCIAL_MATRIX_LINK",
        "phase": 1,
    },
    110: {
        "name": "خروجی خزانه و پرداخت",
        "role": UserRole.TREASURY.value,
        "form_type": "TREASURY_PAYMENT_EXPORT",
        "phase": 4,
    },
}

PROJECT_SEEDS = [
    {
        "project_code": "VOL-CLEAN-1403-01",
        "title": "نظافت ساختمان مرکزی - فروردین ۱۴۰۳",
        "step": 110,
        "start_date": date(2024, 3, 20),
        "end_date": date(2024, 4, 19),
        "amount": 120_000_000,
        "paid_amount": 120_000_000,
        "task_role": UserRole.TREASURY.value,
        "task_status": ApprovalTaskStatus.APPROVED,
        "period_key": "1403-01",
    },
    {
        "project_code": "VOL-CLEAN-1403-02",
        "title": "نظافت مجموعه فرهنگی - اردیبهشت ۱۴۰۳",
        "step": 103,
        "start_date": date(2024, 4, 20),
        "end_date": date(2024, 5, 20),
        "amount": 135_000_000,
        "paid_amount": 0,
        "task_role": UserRole.YEKTA_ADMIN.value,
        "task_status": ApprovalTaskStatus.PENDING,
        "period_key": "1403-02",
    },
    {
        "project_code": "VOL-CLEAN-1403-03",
        "title": "نظافت ساختمان شمالی - خرداد ۱۴۰۳",
        "step": 102,
        "start_date": date(2024, 5, 21),
        "end_date": date(2024, 6, 20),
        "amount": 145_000_000,
        "paid_amount": 0,
        "task_role": UserRole.CONTRACTOR.value,
        "task_status": ApprovalTaskStatus.PENDING,
        "period_key": "1403-03",
    },
]


def ensure_schema() -> None:
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    if not inspector.has_table("contractors"):
        return

    contractor_columns = {column["name"] for column in inspector.get_columns("contractors")}
    if "contractor_type" not in contractor_columns:
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "ALTER TABLE contractors ADD COLUMN contractor_type VARCHAR NOT NULL DEFAULT 'CORPORATE'"
            )


def ensure_user(db: Session) -> User:
    user = db.query(User).filter(User.username == CONTRACTOR_EMAIL).first()
    if user is None:
        user = User(
            username=CONTRACTOR_EMAIL,
            hashed_password=get_password_hash(CONTRACTOR_PASSWORD),
            full_name=CONTRACTOR_NAME,
            role=UserRole.CONTRACTOR.value,
            is_active=True,
            failed_attempts=0,
        )
        db.add(user)
        db.flush()
    else:
        user.hashed_password = get_password_hash(CONTRACTOR_PASSWORD)
        user.full_name = CONTRACTOR_NAME
        user.role = UserRole.CONTRACTOR.value
        user.is_active = True
        user.failed_attempts = 0
        user.locked_until = None
    return user


def ensure_contractor_profile(db: Session, user: User) -> Contractor:
    contractor = db.query(Contractor).filter(Contractor.national_id == CONTRACTOR_NATIONAL_ID).first()
    if contractor is None:
        contractor = Contractor(national_id=CONTRACTOR_NATIONAL_ID, company_name=CONTRACTOR_NAME)
        db.add(contractor)
        db.flush()

    contractor.contractor_type = "CORPORATE"
    contractor.company_name = CONTRACTOR_NAME
    contractor.registration_number = "۴۳۶۲۷۴"
    contractor.ceo_name = "مدیرعامل نمونه"
    contractor.phone = "03132220000"
    contractor.address = "اصفهان، ساختمان مرکزی شهرداری"
    contractor.corporate_id = CONTRACTOR_NATIONAL_ID
    contractor.economic_code = "411111111111"
    contractor.postal_code = "8161111111"
    contractor.province = "اصفهان"
    contractor.city = "اصفهان"
    contractor.bank_name = "ملی"
    contractor.account_number = "010123456789"
    contractor.iban = "IR120170000000123456789001"
    contractor.source_system = "MANUAL"
    contractor.is_verified = True
    contractor.portal_enabled = True

    user.contractor_id = contractor.id
    return contractor


def ensure_defaults(db: Session) -> tuple[OrgUnit, Activity]:
    org = db.query(OrgUnit).filter(OrgUnit.title == "قراردادهای حجمی").first()
    if org is None:
        org = OrgUnit(title="قراردادهای حجمی", code="VOL", org_type="UNIT")
        db.add(org)
        db.flush()

    activity = (
        db.query(Activity)
        .filter(Activity.name == "قراردادهای حجمی و کد یکتا", Activity.org_unit_id == org.id)
        .first()
    )
    if activity is None:
        activity = Activity(
            name="قراردادهای حجمی و کد یکتا",
            org_unit_id=org.id,
            description="فعالیت پیش فرض برای گردش کار قراردادهای حجمی",
            is_active=True,
        )
        db.add(activity)
        db.flush()

    return org, activity


def ensure_step(db: Session, order_index: int) -> WorkflowStep:
    step = db.query(WorkflowStep).filter(WorkflowStep.order_index == order_index).first()
    if step:
        return step

    fallback = STEP_FALLBACKS[order_index]
    definition = (
        db.query(WorkflowStepDefinition)
        .filter(WorkflowStepDefinition.step_number == order_index)
        .first()
    )
    if definition is None:
        definition = WorkflowStepDefinition(
            step_number=order_index,
            name=str(fallback["name"]),
            role_required=str(fallback["role"]),
            required_form_type=str(fallback["form_type"]),
            form_schema={"title": str(fallback["name"]), "type": "object", "properties": {}},
        )
        db.add(definition)
        db.flush()

    step = WorkflowStep(
        code=f"VOLUME_CONTRACT_STEP_{order_index - 100:02d}",
        name=definition.name,
        phase_number=int(fallback["phase"]),
        order_index=order_index,
        step_definition_id=definition.id,
    )
    db.add(step)
    db.flush()
    return step


def project_tracking_prefix(project_code: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "-", project_code).strip("-")
    return f"CIVIL-{normalized or project_code}-DOC-"


def reset_contractor_volume_projects(db: Session, user: User) -> int:
    projects = (
        db.query(CivilProject)
        .filter(CivilProject.contractor_id == user.id, CivilProject.contract_category.isnot(None))
        .all()
    )
    for project in projects:
        prefix = project_tracking_prefix(project.project_code)
        db.query(Transaction).filter(Transaction.tracking_number.like(f"{prefix}%")).delete(
            synchronize_session=False
        )
        db.query(FinancialMatrix).filter(FinancialMatrix.project_id == project.id).delete(
            synchronize_session=False
        )
        db.query(ApprovalTask).filter(ApprovalTask.project_id == project.id).delete(
            synchronize_session=False
        )
        db.query(EntityDocument).filter(EntityDocument.project_id == project.id).delete(
            synchronize_session=False
        )
        db.query(CivilProjectAssignment).filter(CivilProjectAssignment.project_id == project.id).delete(
            synchronize_session=False
        )
        db.delete(project)
    db.flush()
    return len(projects)


def base_payload(seed: dict[str, object]) -> dict[str, object]:
    return {
        "contract_title": seed["title"],
        "contractor_name": CONTRACTOR_NAME,
        "total_amount": int(seed["amount"]),
        "start_date": seed["start_date"].isoformat(),
        "end_date": seed["end_date"].isoformat(),
        "contract_category": CONTRACT_CATEGORY,
    }


def salary_analysis_payload() -> dict[str, int]:
    return {
        "base_salary": 72_000_000,
        "housing_allowance": 9_000_000,
        "grocery_allowance": 11_000_000,
        "child_family_allowance": 4_000_000,
        "overtime_rate": 350_000,
        "employer_insurance_premium": 21_000_000,
    }


def create_documents(
    db: Session,
    project: CivilProject,
    seed: dict[str, object],
    steps: dict[int, WorkflowStep],
    creator: User,
) -> EntityDocument | None:
    db.add(
        EntityDocument(
            project_id=project.id,
            step_id=steps[102].id,
            document_type="VOLUME_CONTRACT_BASE",
            payload=base_payload(seed),
            created_by_id=creator.id,
        )
    )
    db.flush()

    current_step = int(seed["step"])
    if current_step >= 103:
        db.add(
            EntityDocument(
                project_id=project.id,
                step_id=steps[102].id,
                document_type="APPENDIX_5_SALARY_ANALYSIS",
                payload=salary_analysis_payload(),
                created_by_id=creator.id,
            )
        )
        db.flush()

    if current_step < 110:
        return None

    calculation_doc = EntityDocument(
        project_id=project.id,
        step_id=steps[110].id,
        document_type="AUTO_STATEMENT_CALCULATION",
        payload={
            "gross_amount": int(seed["amount"]),
            "work_period": seed["period_key"],
            "statement_number": f"PS-{seed['project_code']}",
            "financial_events": [
                {
                    "event_sequence": 1,
                    "event_code": "NET_PAYMENT",
                    "event_label": "پرداخت خالص پیمانکار",
                    "amount": int(seed["paid_amount"]),
                }
            ],
        },
        created_by_id=creator.id,
    )
    db.add(calculation_doc)
    db.flush()
    return calculation_doc


def create_project(
    db: Session,
    seed: dict[str, object],
    *,
    user: User,
    creator: User,
    org: OrgUnit,
    activity: Activity,
    steps: dict[int, WorkflowStep],
) -> CivilProject:
    step = steps[int(seed["step"])]
    project = CivilProject(
        project_code=str(seed["project_code"]),
        title=str(seed["title"]),
        contract_category=CONTRACT_CATEGORY,
        owning_org_unit_id=org.id,
        activity_id=activity.id,
        created_by_id=creator.id,
        contractor_id=user.id,
        current_step_id=step.id,
        planned_start_date=seed["start_date"],
        planned_end_date=seed["end_date"],
        is_active=True,
        created_at=datetime(2026, 5, 1, 9, 0, 0),
        updated_at=datetime.utcnow(),
    )
    db.add(project)
    db.flush()

    db.add(
        CivilProjectAssignment(
            project_id=project.id,
            user_id=user.id,
            role=CivilProjectRole.CONTRACTOR,
        )
    )

    calculation_doc = create_documents(db, project, seed, steps, creator)

    assignee = user if seed["task_role"] == UserRole.CONTRACTOR.value else None
    task = ApprovalTask(
        project_id=project.id,
        step_id=step.id,
        assigned_role=str(seed["task_role"]),
        assigned_user_id=assignee.id if assignee else None,
        status=seed["task_status"],
        is_required=True,
        comments="داده نمونه داشبورد پیمانکار",
        resolved_at=datetime.utcnow() if seed["task_status"] == ApprovalTaskStatus.APPROVED else None,
    )
    db.add(task)

    paid_amount = int(seed["paid_amount"])
    if paid_amount > 0:
        prefix = project_tracking_prefix(project.project_code)
        transaction = Transaction(
            tracking_number=f"{prefix}PAY-001",
            unique_code=f"YK-{project.project_code}",
            status="APPROVED",
            current_approval_level=4,
            created_by_id=creator.id,
            amount=paid_amount,
            beneficiary_name=CONTRACTOR_NAME,
            contract_number=project.project_code,
            description="پرداخت صورت وضعیت تکمیل شده",
            form_data={
                "financial_event": "NET_PAYMENT",
                "financial_event_label": "پرداخت خالص پیمانکار",
            },
            fiscal_year="1403",
        )
        db.add(transaction)
        db.flush()

        db.add(
            FinancialMatrix(
                project_id=project.id,
                statement_document_id=calculation_doc.id if calculation_doc else None,
                transaction_id=transaction.id,
                budget_line_level_5="VOL-CLEANING-1403",
                cost_center="CLEANING-SERVICES",
                financial_event="NET_PAYMENT",
                financial_event_label="پرداخت خالص پیمانکار",
                event_group="PAYMENT",
                event_sequence=1,
                event_direction="CREDIT",
                activity_name=activity.name,
                period_key=str(seed["period_key"]),
                amount=paid_amount,
                yekta_code=transaction.unique_code,
                payment_queue_status="PAID",
                source_payload={"seed": "contractor_dashboard_demo"},
            )
        )

    return project


def seed() -> dict[str, int]:
    ensure_schema()
    db = SessionLocal()
    try:
        user = ensure_user(db)
        ensure_contractor_profile(db, user)
        creator = db.query(User).filter(User.username == "hr_admin@test.com").first() or user
        org, activity = ensure_defaults(db)
        steps = {order: ensure_step(db, order) for order in (102, 103, 110)}

        deleted_count = reset_contractor_volume_projects(db, user)
        created_count = 0
        for payload in PROJECT_SEEDS:
            create_project(db, payload, user=user, creator=creator, org=org, activity=activity, steps=steps)
            created_count += 1

        db.commit()
        return {"deleted": deleted_count, "created": created_count}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    result = seed()
    print("Contractor demo seed completed.")
    print(f"Deleted old volume projects for {CONTRACTOR_EMAIL}: {result['deleted']}")
    print(f"Created demo projects: {result['created']}")
    print(f"Login: {CONTRACTOR_EMAIL} / {CONTRACTOR_PASSWORD}")

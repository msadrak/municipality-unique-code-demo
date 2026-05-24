from __future__ import annotations

import sys
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import inspect
from sqlalchemy.orm import Session

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.security import get_password_hash
from app.database import SessionLocal, engine
from app.models import (
    Activity,
    ApprovalTask,
    ApprovalTaskStatus,
    Base,
    BudgetItem,
    CivilProject,
    CivilProjectAssignment,
    CivilProjectRole,
    Contract,
    ContractStatus,
    Contractor,
    EntityDocument,
    FinancialRule,
    OrgUnit,
    StepAction,
    Transaction,
    User,
    WorkflowStep,
    WorkflowStepDefinition,
    WorkflowTransition,
)
from app.models.enums import UserRole


PROJECT_CODE = "CIVIL-GRAND-SOMAYEH-1405"
PROJECT_TITLE = "احداث و تجهیز بوستان سمیه"
TOTAL_BUDGET = 20_000_000_000
COMMITTED_AMOUNT = 18_500_000_000
CONTRACTOR_NAME = "شرکت عمران سبز سمیه"
CONTRACT_NUMBER = "CNT-SOMAYEH-1405-020"
DEFAULT_PASSWORD = "password123"


_LEGACY_STEP_BLUEPRINTS: tuple[tuple[int, str, str, str | None, str | None], ...] = (
    (1, "ثبت درخواست پروژه", UserRole.CIVIL_MANAGER.value, "PROJECT_REQUEST", None),
    (2, "بررسی اولیه درخواست", UserRole.CIVIL_MANAGER.value, "PRELIMINARY_REVIEW", None),
    (3, "بازدید و برداشت میدانی", UserRole.SUPERVISOR.value, "SITE_SURVEY_REPORT", None),
    (4, "برآورد اولیه و ریزمتره", UserRole.SUPERVISOR.value, "ESTIMATE_SHEET", None),
    (5, "تحویل زمین", UserRole.DELIVERY_COMMISSION.value, "LAND_HANDOVER", None),
    (6, "تهیه مدارک طراحی", UserRole.CIVIL_MANAGER.value, "DESIGN_PACKAGE", None),
    (7, "تایید فنی نقشه‌ها", UserRole.CIVIL_MANAGER.value, "TECHNICAL_APPROVAL", None),
    (8, "مسدودسازی اعتبار", UserRole.FINANCE_MANAGER.value, "BUDGET_BLOCK_REQUEST", "BUDGET_BLOCKED"),
    (9, "تهیه اسناد مناقصه", UserRole.TENDERING_OFFICER.value, "TENDER_PACKAGE", None),
    (10, "انتشار فراخوان مناقصه", UserRole.TENDERING_OFFICER.value, "TENDER_NOTICE", None),
    (11, "صورتجلسه بازگشایی پاکات", UserRole.TENDERING_OFFICER.value, "BID_OPENING_MINUTES", None),
    (12, "ارزیابی پیشنهادها", UserRole.TENDERING_OFFICER.value, "BID_EVALUATION_REPORT", None),
    (13, "ابلاغ برنده مناقصه", UserRole.CIVIL_MANAGER.value, "WINNER_APPROVAL", None),
    (14, "تنظیم پیش‌نویس قرارداد", UserRole.CONTRACTS_OFFICER.value, "CONTRACT_DRAFT", None),
    (15, "تعهد قرارداد", UserRole.CONTRACTS_OFFICER.value, "CONTRACT_SIGNED", "CONTRACT_COMMITTED"),
    (16, "تحویل کارگاه به پیمانکار", UserRole.DELIVERY_COMMISSION.value, "SITE_MOBILIZATION", None),
    (17, "تعیین ناظر مقیم", UserRole.CIVIL_MANAGER.value, "SUPERVISOR_ASSIGNMENT", None),
    (18, "ابلاغ دستور شروع کار", UserRole.CONTRACTS_OFFICER.value, "START_ORDER", None),
    (19, "ثبت گزارش روزانه عملیات", UserRole.SUPERVISOR.value, "DAILY_REPORT", None),
    (20, "تهیه صورت‌وضعیت", UserRole.SUPERVISOR.value, "PROGRESS_STATEMENT", None),
    (21, "ایجاد سند مالی", UserRole.FINANCE_MANAGER.value, "PAYMENT_REQUEST", "TRANSACTION_CREATED"),
    (22, "کنترل و تایید مالی", UserRole.FINANCE_MANAGER.value, "FINANCE_REVIEW", None),
    (23, "استعلام و تایید حراست", "SECURITY", "SECURITY_CLEARANCE", None),
    (24, "تایید شهردار", "MAYOR", "MAYOR_APPROVAL", "PAYMENT_APPROVED"),
    (25, "صدور دستور پرداخت", UserRole.FINANCE_MANAGER.value, "PAYMENT_ORDER", None),
    (26, "گزارش اتمام عملیات", UserRole.SUPERVISOR.value, "COMPLETION_REPORT", None),
    (27, "صورتجلسه کمیسیون", UserRole.DELIVERY_COMMISSION.value, "COMMISSION_MINUTES", None),
    (28, "تحویل موقت پروژه", UserRole.DELIVERY_COMMISSION.value, "TEMPORARY_HANDOVER", None),
    (29, "دوره رفع نقص", UserRole.SUPERVISOR.value, "DEFECTS_LIABILITY_REPORT", None),
    (30, "آزادسازی تضمین‌ها", UserRole.FINANCE_MANAGER.value, "GUARANTEE_RELEASE", "GUARANTEE_RELEASED"),
    (31, "اختتام و بایگانی پرونده", UserRole.CIVIL_MANAGER.value, "CLOSEOUT_ARCHIVE", None),
)


STEP_BLUEPRINTS = (
    (1, "تعریف پروژه برای سال آینده...", UserRole.CIVIL_MANAGER.value, "NEXT_YEAR_PROJECT_DEFINITION", None),
    (2, "تصویب بودجه شورا", UserRole.FINANCE_MANAGER.value, "COUNCIL_BUDGET_APPROVAL", "BUDGET_BLOCKED"),
    (3, "تخمین ریالی هزینه انجام", UserRole.CIVIL_MANAGER.value, "COST_ESTIMATE", None),
    (4, "ثبت در سامانه های مربوطه...", UserRole.CIVIL_MANAGER.value, "SYSTEM_REGISTRATION", None),
    (5, "ارسال به سازمان طراحی...", UserRole.CIVIL_MANAGER.value, "DESIGN_ORG_REFERRAL", None),
    (6, "برگزاری جلسات کمیته فنی فاز 1", UserRole.CIVIL_MANAGER.value, "TECHNICAL_COMMITTEE_PHASE_1", None),
    (7, "برگزاری جلسات اولویت بندی زمان طراحی", UserRole.CIVIL_MANAGER.value, "DESIGN_PRIORITY_MEETING", None),
    (8, "تهیه فرم های مستندسازی...", UserRole.CIVIL_MANAGER.value, "DOCUMENTATION_FORMS", None),
    (9, "تکمیل اطلاعات درخواستی طراحی...", UserRole.CIVIL_MANAGER.value, "DESIGN_REQUEST_COMPLETION", None),
    (10, "برگزاری جلسات کمیته فنی فاز 2", UserRole.CIVIL_MANAGER.value, "TECHNICAL_COMMITTEE_PHASE_2", None),
    (11, "بررسی طرح توسط کارشناسان معاونت عمران", UserRole.CIVIL_MANAGER.value, "DEPUTY_TECHNICAL_REVIEW", None),
    (12, "با توجه به مبلغ برآورد: صورت استعلام/مناقصه", UserRole.TENDERING_OFFICER.value, "PROCUREMENT_METHOD_DECISION", None),
    (13, "مرحله 10 - در انتظار تعیین کارفرما", UserRole.CIVIL_MANAGER.value, None, None),
    (14, "دعوتنامه شرکت در کمیسیون", UserRole.TENDERING_OFFICER.value, "COMMISSION_INVITATION", None),
    (15, "شرکت در جلسه کمیسیون و تعیین برنده", UserRole.TENDERING_OFFICER.value, "COMMISSION_WINNER_SELECTION", None),
    (16, "دعوتنامه برای پیمانکار برنده", UserRole.CONTRACTS_OFFICER.value, "WINNING_CONTRACTOR_INVITATION", None),
    (17, "تهیه قرارداد و امضاء مسئولین", UserRole.CONTRACTS_OFFICER.value, "CONTRACT_SIGNED", "CONTRACT_COMMITTED"),
    (18, "ابلاغ قرارداد به پیمانکار", UserRole.CONTRACTS_OFFICER.value, "CONTRACT_NOTICE_TO_CONTRACTOR", None),
    (19, "ابلاغ ناظر به پیمانکار", UserRole.CIVIL_MANAGER.value, "SUPERVISOR_NOTICE_TO_CONTRACTOR", None),
    (20, "دعوتنامه تحویل زمین", UserRole.DELIVERY_COMMISSION.value, "LAND_HANDOVER_INVITATION", None),
    (21, "صورتجلسه تحویل زمین", UserRole.DELIVERY_COMMISSION.value, "LAND_HANDOVER", None),
    (22, "ابلاغ تحویل زمین", UserRole.CONTRACTS_OFFICER.value, "LAND_HANDOVER_NOTICE", None),
    (23, "ارائه صورتوضعیت پیمانکار به ناظر", UserRole.CONTRACTOR.value, "CONTRACTOR_PROGRESS_STATEMENT", None),
    (24, "تهیه روکش توسط کارشناس پیمان", UserRole.CONTRACTS_OFFICER.value, "CONTRACT_COVER_SHEET", None),
    (25, "تکمیل امضا، و شماره شدن روکش", UserRole.CONTRACTS_OFFICER.value, "COVER_SHEET_SIGNATURES", None),
    (26, "واحد رسیدگی مجدد", UserRole.FINANCE_MANAGER.value, "REVIEW_UNIT_RECHECK", None),
    (27, "درخواست تحویل موقت", UserRole.CONTRACTOR.value, "TEMPORARY_HANDOVER_REQUEST", None),
    (28, "درخواست سیستمی از منطقه به معاونت", UserRole.CIVIL_MANAGER.value, "REGION_TO_DEPUTY_REQUEST", None),
    (29, "دعوتنامه تحویل موقت", UserRole.DELIVERY_COMMISSION.value, "TEMPORARY_HANDOVER_INVITATION", None),
    (30, "صورتجلسه تحویل موقت و امضاها (هوشمند)", UserRole.DELIVERY_COMMISSION.value, "TEMPORARY_HANDOVER_MINUTES", None),
    (31, "ابلاغ تحویل موقت و آزادسازی ضمانتنامه", UserRole.FINANCE_MANAGER.value, "TEMPORARY_HANDOVER_NOTICE_GUARANTEE_RELEASE", "GUARANTEE_RELEASED"),
    (32, "ارسال اطلاعات مالی مناطق", UserRole.FINANCE_MANAGER.value, "REGIONAL_FINANCIAL_DATA", None),
    (33, "صورت وضعیت قطعی و تعدیل قطعی (هوشمند)", UserRole.FINANCE_MANAGER.value, "PROGRESS_STATEMENT", "TRANSACTION_CREATED"),
    (34, "ابلاغ 25% مازاد بر قرارداد", UserRole.CONTRACTS_OFFICER.value, "CONTRACT_SURPLUS_25_NOTICE", None),
    (35, "درخواست تحویل قطعی پیمانکار", UserRole.CONTRACTOR.value, "FINAL_HANDOVER_REQUEST", None),
    (36, "درخواست سیستمی جهت معاونت جهت تایید", UserRole.CIVIL_MANAGER.value, "FINAL_HANDOVER_DEPUTY_APPROVAL_REQUEST", None),
    (37, "دعوتنامه تحویل قطعی", UserRole.DELIVERY_COMMISSION.value, "FINAL_HANDOVER_INVITATION", None),
    (38, "صورتجلسه تحویل قطعی (هوشمند)", UserRole.DELIVERY_COMMISSION.value, "FINAL_HANDOVER_MINUTES", None),
    (39, "ابلاغ تحویل قطعی", UserRole.CONTRACTS_OFFICER.value, "FINAL_HANDOVER_NOTICE", None),
)


PROGRESS_STATEMENT_SCHEMA: dict[str, Any] = {
    "title": "فرم تهیه صورت‌وضعیت پیمانکار",
    "description": "اطلاعات صورت‌وضعیت مرحله‌ای بوستان سمیه را وارد کنید.",
    "type": "object",
    "properties": {
        "invoice_number": {
            "type": "string",
            "title": "شماره صورت‌وضعیت",
            "placeholder": "PS-SOMAYEH-001",
        },
        "period": {
            "type": "string",
            "title": "دوره کارکرد",
            "placeholder": "فروردین ۱۴۰۵",
        },
        "gross_amount": {
            "type": "number",
            "title": "مبلغ ناخالص",
            "placeholder": "2500000000",
        },
        "contractor_name": {
            "type": "string",
            "title": "نام پیمانکار",
            "placeholder": CONTRACTOR_NAME,
        },
        "contract_number": {
            "type": "string",
            "title": "شماره قرارداد",
            "placeholder": CONTRACT_NUMBER,
        },
        "description": {
            "type": "string",
            "title": "شرح عملیات",
            "widget": "textarea",
            "placeholder": "اجرای مسیر سلامت، کف‌سازی، روشنایی و تجهیز محوطه بازی",
        },
    },
    "required": ["invoice_number", "period", "gross_amount", "contractor_name", "contract_number"],
}


PHASE_1_STEP_1_SCHEMA: dict[str, Any] = {
    "title": "تعریف پروژه برای سال آینده",
    "description": "فقط اطلاعات پایه را وارد کنید و مدارک فنی، فرم‌های طراحی و مستندات تفصیلی را در بخش پیوست‌ها بارگذاری کنید.",
    "type": "object",
    "properties": {
        "project_title": {
            "type": "string",
            "title": "عنوان پروژه",
            "placeholder": PROJECT_TITLE,
        },
        "reference_number": {
            "type": "string",
            "title": "شماره نامه / ارجاع",
            "placeholder": "REF-1405-001",
        },
    },
    "required": ["project_title", "reference_number"],
}


TEMPORARY_HANDOVER_SCHEMA: dict[str, Any] = {
    "title": "صورتجلسه تحویل موقت و امضاها",
    "type": "object",
    "additionalProperties": True,
    "properties": {
        "meeting_date": {"type": "string", "title": "تاریخ جلسه"},
        "commission_members": {"type": "string", "title": "اعضای کمیسیون", "widget": "textarea"},
        "decisions": {"type": "string", "title": "مصوبات", "widget": "textarea"},
    },
}


FINAL_HANDOVER_SCHEMA: dict[str, Any] = {
    "title": "صورتجلسه تحویل قطعی",
    "type": "object",
    "additionalProperties": True,
    "properties": {
        "handover_date": {"type": "string", "title": "تاریخ تحویل قطعی"},
        "commission_members": {"type": "string", "title": "اعضای کمیسیون", "widget": "textarea"},
        "final_decision": {"type": "string", "title": "نتیجه نهایی", "widget": "textarea"},
    },
}


SMART_FORM_SCHEMAS: dict[int, dict[str, Any]] = {
    1: PHASE_1_STEP_1_SCHEMA,
    30: TEMPORARY_HANDOVER_SCHEMA,
    33: PROGRESS_STATEMENT_SCHEMA,
    38: FINAL_HANDOVER_SCHEMA,
}


def phase_for_step(step_number: int) -> int:
    if step_number <= 11:
        return 1
    if step_number <= 18:
        return 2
    if step_number <= 34:
        return 3
    return 4


def ensure_demo_schema() -> None:
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    timestamp_type = "TIMESTAMP" if engine.dialect.name == "postgresql" else "DATETIME"
    json_type = "JSONB" if engine.dialect.name == "postgresql" else "JSON"

    with engine.begin() as connection:
        if inspector.has_table("workflow_step_definitions"):
            columns = {column["name"] for column in inspector.get_columns("workflow_step_definitions")}
            if "form_schema" not in columns:
                connection.exec_driver_sql(
                    f"ALTER TABLE workflow_step_definitions ADD COLUMN form_schema {json_type}"
                )

        if inspector.has_table("workflow_steps"):
            columns = {column["name"] for column in inspector.get_columns("workflow_steps")}
            if "step_definition_id" not in columns:
                connection.exec_driver_sql(
                    "ALTER TABLE workflow_steps ADD COLUMN step_definition_id INTEGER"
                )

        if inspector.has_table("approval_tasks"):
            columns = {column["name"] for column in inspector.get_columns("approval_tasks")}
            if "step_action_id" not in columns:
                connection.exec_driver_sql("ALTER TABLE approval_tasks ADD COLUMN step_action_id INTEGER")
            if "is_required" not in columns:
                connection.exec_driver_sql(
                    "ALTER TABLE approval_tasks ADD COLUMN is_required BOOLEAN DEFAULT TRUE NOT NULL"
                )
            if "resolved_at" not in columns:
                connection.exec_driver_sql(
                    f"ALTER TABLE approval_tasks ADD COLUMN resolved_at {timestamp_type}"
                )


def upsert_user(
    db: Session,
    *,
    username: str,
    full_name: str,
    role: UserRole,
    zone: OrgUnit,
    contractor: Contractor | None = None,
) -> User:
    user = db.query(User).filter(User.username == username).first()
    values = {
        "full_name": full_name,
        "role": role.value,
        "region_name": zone.title,
        "contractor_id": contractor.id if contractor else None,
        "default_zone_id": zone.id,
        "is_active": True,
        "failed_attempts": 0,
        "hashed_password": get_password_hash(DEFAULT_PASSWORD),
    }
    if user:
        for key, value in values.items():
            setattr(user, key, value)
        return user

    user = User(username=username, **values)
    db.add(user)
    db.flush()
    return user


def upsert_definition(
    db: Session,
    step_number: int,
    name: str,
    role_required: str,
    required_form_type: str | None,
    financial_gate: str | None,
) -> WorkflowStepDefinition:
    definition = (
        db.query(WorkflowStepDefinition)
        .filter(WorkflowStepDefinition.step_number == step_number)
        .first()
    )
    if definition is None:
        definition = WorkflowStepDefinition(step_number=step_number)
        db.add(definition)
        db.flush()

    definition.name = name
    definition.role_required = role_required
    definition.required_form_type = required_form_type
    definition.financial_gate = financial_gate
    definition.form_schema = SMART_FORM_SCHEMAS.get(step_number)
    return definition


def upsert_step(
    db: Session,
    *,
    step_number: int,
    definition: WorkflowStepDefinition,
) -> WorkflowStep:
    code = f"CIVIL_STEP_{step_number:02d}"
    step = db.query(WorkflowStep).filter(WorkflowStep.order_index == step_number).first()
    if step is None:
        step = WorkflowStep(code=code, order_index=step_number)
        db.add(step)
        db.flush()

    step.code = code
    step.name = definition.name
    step.phase_number = phase_for_step(step_number)
    step.step_definition_id = definition.id
    return step


def ensure_transition(db: Session, from_step: WorkflowStep, to_step: WorkflowStep) -> None:
    transition = (
        db.query(WorkflowTransition)
        .filter(
            WorkflowTransition.from_step_id == from_step.id,
            WorkflowTransition.to_step_id == to_step.id,
            WorkflowTransition.required_role.is_(None),
        )
        .first()
    )
    if transition:
        transition.is_automatic = False
        return

    db.add(
        WorkflowTransition(
            from_step_id=from_step.id,
            to_step_id=to_step.id,
            required_role=None,
            is_automatic=False,
        )
    )


def ensure_required_action(
    db: Session,
    *,
    step: WorkflowStep,
    assigned_role: str,
    order_index: int = 1,
) -> StepAction:
    action = (
        db.query(StepAction)
        .filter(
            StepAction.step_definition_id == step.definition.id,
            StepAction.assigned_role == assigned_role,
        )
        .first()
    )
    if action is None:
        action = StepAction(
            step_definition_id=step.definition.id,
            assigned_role=assigned_role,
        )
        db.add(action)
    action.is_required = True
    action.order_index = order_index
    return action


def ensure_workflow(db: Session) -> dict[int, WorkflowStep]:
    steps: dict[int, WorkflowStep] = {}
    for step_number, name, role_required, required_form_type, financial_gate in STEP_BLUEPRINTS:
        definition = upsert_definition(
            db,
            step_number,
            name,
            role_required,
            required_form_type,
            financial_gate,
        )
        steps[step_number] = upsert_step(db, step_number=step_number, definition=definition)

    db.flush()
    db.query(WorkflowTransition).filter(
        WorkflowTransition.from_step_id.in_([step.id for step in steps.values()])
    ).delete(synchronize_session=False)

    for step_number in range(1, len(STEP_BLUEPRINTS)):
        ensure_transition(db, steps[step_number], steps[step_number + 1])

    ensure_required_action(
        db,
        step=steps[33],
        assigned_role=UserRole.FINANCE_MANAGER.value,
    )
    db.flush()
    return steps


def upsert_document(
    db: Session,
    *,
    project: CivilProject,
    step: WorkflowStep,
    document_type: str,
    payload: dict[str, Any],
    created_by: User,
    created_at: datetime,
) -> EntityDocument:
    document = (
        db.query(EntityDocument)
        .filter(
            EntityDocument.project_id == project.id,
            EntityDocument.step_id == step.id,
            EntityDocument.document_type == document_type,
        )
        .first()
    )
    if document is None:
        document = EntityDocument(
            project_id=project.id,
            step_id=step.id,
            document_type=document_type,
            payload=payload,
            created_by_id=created_by.id,
            created_at=created_at,
        )
        db.add(document)
    else:
        document.payload = payload
        document.created_by_id = created_by.id
        document.created_at = created_at
    db.flush()
    return document


def ensure_assignment(db: Session, project: CivilProject, user: User, role: CivilProjectRole) -> None:
    assignment = (
        db.query(CivilProjectAssignment)
        .filter(
            CivilProjectAssignment.project_id == project.id,
            CivilProjectAssignment.user_id == user.id,
            CivilProjectAssignment.role == role,
        )
        .first()
    )
    if assignment is None:
        assignment = CivilProjectAssignment(project_id=project.id, user_id=user.id, role=role)
        db.add(assignment)
    assignment.is_active = True


def civil_tracking_prefix(project_code: str, project_id: int) -> str:
    normalized_project_code = re.sub(r"[^A-Za-z0-9]+", "-", project_code).strip("-")
    if not normalized_project_code:
        normalized_project_code = f"PROJECT-{project_id}"
    return f"CIVIL-{normalized_project_code}-DOC-"


def seed() -> None:
    ensure_demo_schema()
    db = SessionLocal()
    try:
        print("Preparing workflow blueprint...")
        steps = ensure_workflow(db)

        zone = db.query(OrgUnit).filter(OrgUnit.code == "14").first()
        if zone is None:
            zone = OrgUnit(title="منطقه ۱۴", code="14", org_type="ZONE")
            db.add(zone)
            db.flush()
        else:
            zone.title = "منطقه ۱۴"
            zone.org_type = "ZONE"

        activity = (
            db.query(Activity)
            .filter(Activity.org_unit_id == zone.id, Activity.name == "احداث و توسعه فضای سبز")
            .first()
        )
        if activity is None:
            activity = Activity(org_unit_id=zone.id, name="احداث و توسعه فضای سبز")
            db.add(activity)
            db.flush()
        activity.description = "بودجه عمرانی برای احداث، تجهیز و بهسازی بوستان‌های منطقه ۱۴"
        activity.is_active = True

        budget_item = db.query(BudgetItem).filter(BudgetItem.budget_code == "BL-SOMAYEH-PARK-1405").first()
        if budget_item is None:
            budget_item = BudgetItem(budget_code="BL-SOMAYEH-PARK-1405")
            db.add(budget_item)
            db.flush()
        budget_item.description = "احداث و تجهیز بوستان سمیه"
        budget_item.budget_type = "capital"
        budget_item.zone = zone.title
        budget_item.zone_code = zone.code
        budget_item.subject = "فضای سبز شهری"
        budget_item.sub_subject = PROJECT_TITLE
        budget_item.row_type = "پروژه‌ای"
        budget_item.approved_1403 = float(TOTAL_BUDGET)
        budget_item.allocated_1403 = float(TOTAL_BUDGET)
        budget_item.spent_1403 = 0
        budget_item.reserved_amount = float(COMMITTED_AMOUNT)
        budget_item.remaining_budget = float(TOTAL_BUDGET - COMMITTED_AMOUNT)

        rule = (
            db.query(FinancialRule)
            .filter(
                FinancialRule.activity_id == activity.id,
                FinancialRule.budget_line_code == budget_item.budget_code,
            )
            .first()
        )
        if rule is None:
            rule = FinancialRule(activity_id=activity.id, budget_line_code=budget_item.budget_code)
            db.add(rule)
        rule.cost_center_code = "CC-R14-PARKS"
        rule.financial_event_type = "CIVIL_PROGRESS_PAYMENT"
        rule.is_active = True

        contractor = db.query(Contractor).filter(Contractor.national_id == "1405014001").first()
        if contractor is None:
            contractor = Contractor(national_id="1405014001", company_name=CONTRACTOR_NAME)
            db.add(contractor)
            db.flush()
        contractor.company_name = CONTRACTOR_NAME
        contractor.registration_number = "558721"
        contractor.ceo_name = "رضا نیک‌فر"
        contractor.phone = "021-77884521"
        contractor.address = "تهران، منطقه ۱۴، خیابان پیروزی، دفتر پروژه بوستان سمیه"
        contractor.province = "تهران"
        contractor.city = "تهران"
        contractor.bank_name = "بانک شهر"
        contractor.iban = "IR120610000000120501400101"
        contractor.source_system = "MANUAL"
        contractor.is_verified = True
        contractor.portal_enabled = True

        civil_manager = upsert_user(
            db,
            username="civil.demo@municipality.local",
            full_name="مدیر عمران منطقه ۱۴",
            role=UserRole.CIVIL_MANAGER,
            zone=zone,
        )
        supervisor = upsert_user(
            db,
            username="supervisor.demo@municipality.local",
            full_name="مهندس مریم نادری",
            role=UserRole.SUPERVISOR,
            zone=zone,
        )
        contracts_officer = upsert_user(
            db,
            username="contracts.demo@municipality.local",
            full_name="کارشناس قراردادها",
            role=UserRole.CONTRACTS_OFFICER,
            zone=zone,
        )
        delivery_user = upsert_user(
            db,
            username="delivery.demo@municipality.local",
            full_name="دبیر کمیسیون تحویل",
            role=UserRole.DELIVERY_COMMISSION,
            zone=zone,
        )
        finance_user = upsert_user(
            db,
            username="finance.demo@municipality.local",
            full_name="ذی‌حساب عمران",
            role=UserRole.FINANCE_MANAGER,
            zone=zone,
        )
        contractor_user = upsert_user(
            db,
            username="contractor.somayeh@municipality.local",
            full_name=CONTRACTOR_NAME,
            role=UserRole.CONTRACTOR,
            zone=zone,
            contractor=contractor,
        )

        project = db.query(CivilProject).filter(CivilProject.project_code == PROJECT_CODE).first()
        if project is None:
            project = CivilProject(
                project_code=PROJECT_CODE,
                title=PROJECT_TITLE,
                owning_org_unit_id=zone.id,
                activity_id=activity.id,
                created_by_id=civil_manager.id,
                current_step_id=steps[33].id,
                planned_start_date=date(2026, 3, 21),
                planned_end_date=date(2026, 11, 20),
                is_active=True,
            )
            db.add(project)
            db.flush()
        project.title = PROJECT_TITLE
        project.owning_org_unit_id = zone.id
        project.activity_id = activity.id
        project.created_by_id = civil_manager.id
        project.current_step_id = steps[33].id
        project.planned_start_date = date(2026, 3, 21)
        project.planned_end_date = date(2026, 11, 20)
        project.is_active = True
        project.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

        for role, user in (
            (CivilProjectRole.CIVIL_MANAGER, civil_manager),
            (CivilProjectRole.SUPERVISOR, supervisor),
            (CivilProjectRole.CONTRACTS_OFFICER, contracts_officer),
            (CivilProjectRole.DELIVERY_COMMISSION, delivery_user),
            (CivilProjectRole.FINANCE_MANAGER, finance_user),
            (CivilProjectRole.CONTRACTOR, contractor_user),
        ):
            ensure_assignment(db, project, user, role)

        contract = db.query(Contract).filter(Contract.contract_number == CONTRACT_NUMBER).first()
        if contract is None:
            contract = Contract(
                contract_number=CONTRACT_NUMBER,
                title=f"قرارداد {PROJECT_TITLE}",
                contractor_id=contractor.id,
                total_amount=COMMITTED_AMOUNT,
            )
            db.add(contract)
            db.flush()
        contract.title = f"قرارداد {PROJECT_TITLE}"
        contract.contractor_id = contractor.id
        contract.civil_project_id = project.id
        contract.org_unit_id = zone.id
        contract.status = ContractStatus.IN_PROGRESS
        contract.total_amount = COMMITTED_AMOUNT
        contract.paid_amount = 0
        contract.start_date = date(2026, 4, 4)
        contract.end_date = date(2026, 11, 20)
        contract.created_by_id = contracts_officer.id
        contract.template_data = {
            "project_title": PROJECT_TITLE,
            "contractor_name": CONTRACTOR_NAME,
            "committed_amount": COMMITTED_AMOUNT,
            "budget_line_code": budget_item.budget_code,
        }

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        upsert_document(
            db,
            project=project,
            step=steps[21],
            document_type="LAND_HANDOVER",
            created_by=delivery_user,
            created_at=now - timedelta(days=47),
            payload={
                "delivery_date": "1405/01/09",
                "inspection_date": "1405/01/08",
                "initial_amount": TOTAL_BUDGET,
                "project_code": PROJECT_CODE,
                "contractor_name": CONTRACTOR_NAME,
                "supervisor_name": supervisor.full_name,
                "handover_location": "منطقه ۱۴، محله سمیه، قطعه فضای سبز ضلع شرقی",
                "land_area": "۱۲,۴۵۰ متر مربع",
                "municipality_representative": "مهندس سعید بهرامی",
                "contractor_representative": "رضا نیک‌فر",
                "notes": "زمین بدون معارض و آماده تجهیز کارگاه تحویل پیمانکار شد.",
            },
        )
        upsert_document(
            db,
            project=project,
            step=steps[17],
            document_type="CONTRACT_SIGNED",
            created_by=contracts_officer,
            created_at=now - timedelta(days=25),
            payload={
                "contract_number": CONTRACT_NUMBER,
                "contractor_name": CONTRACTOR_NAME,
                "committed_amount": COMMITTED_AMOUNT,
                "contract_date": "1405/01/27",
                "start_date": "1405/01/30",
                "end_date": "1405/08/29",
                "supervisor_name": supervisor.full_name,
                "budget_line_code": budget_item.budget_code,
                "scope": "اجرای مسیر سلامت، کف‌سازی، روشنایی، فضای بازی کودک، مبلمان شهری و کاشت فضای سبز",
            },
        )

        db.query(Transaction).filter(
            Transaction.tracking_number.like(f"{civil_tracking_prefix(project.project_code, project.id)}%")
        ).delete(synchronize_session=False)
        db.query(ApprovalTask).filter(
            ApprovalTask.project_id == project.id,
        ).delete(synchronize_session=False)
        db.query(EntityDocument).filter(
            EntityDocument.project_id == project.id,
            EntityDocument.step_id == steps[33].id,
            EntityDocument.document_type == "PROGRESS_STATEMENT",
        ).delete(synchronize_session=False)

        step33_action = (
            db.query(StepAction)
            .filter(
                StepAction.step_definition_id == steps[33].definition.id,
                StepAction.assigned_role == UserRole.FINANCE_MANAGER.value,
            )
            .one()
        )
        task = ApprovalTask(
            project_id=project.id,
            step_id=steps[33].id,
            step_action_id=step33_action.id,
            assigned_role=UserRole.FINANCE_MANAGER.value,
            assigned_user_id=finance_user.id,
            status=ApprovalTaskStatus.PENDING,
            is_required=True,
            comments="آماده بررسی صورت‌وضعیت مرحله‌ای در جلسه دمو",
        )
        db.add(task)

        db.commit()
        db.refresh(project)
        db.refresh(task)

        print("")
        print("Grand demo seed complete.")
        print(f"Project: {project.project_code} - {project.title}")
        print("Current step: 33 - صورت وضعیت قطعی و تعدیل قطعی (هوشمند)")
        print(f"Budget matrix: {TOTAL_BUDGET:,} IRR")
        print(f"Contract commitment: {COMMITTED_AMOUNT:,} IRR")
        print(f"Pending task: #{task.id} for {finance_user.username} ({finance_user.role})")
        print(f"Demo login: {finance_user.username} / {DEFAULT_PASSWORD}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()

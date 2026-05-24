"""Seed the isolated Volume Contracts & Yekta Code workflow.

This script is intentionally idempotent. It creates the missing workflow
definition/category mapping structures, then upserts the 4-step workflow using
the existing BPMS step/action/transition tables.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database import SessionLocal  # noqa: E402
from app.models import StepAction, WorkflowStep, WorkflowStepDefinition, WorkflowTransition  # noqa: E402


WORKFLOW_CODE = "VOLUME_CONTRACTS_YEKTA"
WORKFLOW_NAME = "قراردادهای حجمی و کد یکتا"
STEP_OFFSET = 100

VOLUME_CONTRACT_CATEGORIES = [
    "نظافت و پذیرایی",
    "مجموعه تخت فولاد",
    "ویلاهای چادگان",
    "ویلاهای چابکسر",
    "مجموعه هشت بهشت",
    "زائرسرای مشهد",
    "ترابری و لجستیک",
    "ساختمان خانه مطبوعات",
    "ساماندهی اتباع خارجی",
    "خدمات پیرایشگری",
    "حفاظت فیزیکی",
]


def field(field_type: str, title: str, **extra: object) -> dict[str, object]:
    payload: dict[str, object] = {"type": field_type, "title": title}
    payload.update(extra)
    return payload


STEP_BLUEPRINTS = [
    {
        "order": 1,
        "name": "ثبت پایه قرارداد",
        "role": "HR_ADMIN",
        "form_type": "VOLUME_CONTRACT_BASE",
        "schema": {
            "title": "ثبت پایه قرارداد حجمی",
            "type": "object",
            "properties": {
                "contract_title": field("string", "عنوان قرارداد"),
                "contractor_name": field("string", "نام پیمانکار"),
                "total_amount": field("number", "مبلغ کل قرارداد"),
                "start_date": field("string", "تاریخ شروع", format="date"),
                "end_date": field("string", "تاریخ پایان", format="date"),
                "contract_category": field("string", "دسته قرارداد"),
            },
            "required": ["contract_title", "contractor_name", "total_amount", "start_date", "end_date"],
        },
    },
    {
        "order": 2,
        "name": "تدقیق آنالیز حقوق - پیوست ۵",
        "role": "HR_ADMIN",
        "form_type": "APPENDIX_5_SALARY_ANALYSIS",
        "schema": {
            "title": "تدقیق آنالیز حقوق - پیوست ۵",
            "description": "دیجیتالی‌سازی پیوست ۵ قرارداد برای محاسبات خودکار حقوق و کسورات.",
            "type": "object",
            "properties": {
                "base_salary": field("number", "حقوق پایه"),
                "housing_allowance": field("number", "حق مسکن"),
                "grocery_allowance": field("number", "بن خواروبار"),
                "child_family_allowance": field("number", "حق اولاد / عائله‌مندی"),
                "overtime_rate": field("number", "نرخ اضافه‌کار"),
                "employer_insurance_premium": field("number", "حق بیمه سهم کارفرما"),
            },
            "required": [
                "base_salary",
                "housing_allowance",
                "grocery_allowance",
                "child_family_allowance",
                "overtime_rate",
                "employer_insurance_premium",
            ],
        },
    },
    {
        "order": 3,
        "name": "تخصیص ماتریس مالی",
        "role": "FINANCE_MANAGER",
        "form_type": "FINANCIAL_MATRIX_LINK",
        "schema": {
            "title": "تخصیص ماتریس مالی",
            "type": "object",
            "properties": {
                "budget_line_level_5": field("string", "ردیف بودجه سطح ۵"),
                "cost_center": field("string", "مرکز هزینه"),
            },
            "required": ["budget_line_level_5", "cost_center"],
        },
    },
    {
        "order": 4,
        "name": "تایید اتصال ماتریس مالی",
        "role": "YEKTA_ADMIN",
        "form_type": "YEKTA_CODE_ISSUANCE",
        "schema": {
            "title": "تایید اتصال ماتریس مالی",
            "type": "object",
            "properties": {
                "confirm_financial_matrix": field("boolean", "تایید آمادگی ماتریس برای صورت‌وضعیت‌های آتی"),
            },
            "required": ["confirm_financial_matrix"],
        },
    },
    {
        "order": 5,
        "name": "بارگذاری صورت‌وضعیت و فایل‌های اکسل",
        "role": "CONTRACTOR",
        "approval_role": "YEKTA_ADMIN",
        "form_type": "APPENDIX_5_TIMESHEET",
        "schema": {
            "title": "بارگذاری صورت‌وضعیت پیمانکار",
            "description": "پیمانکار صورت‌وضعیت رسمی، فایل ۱۸ ستونی و فایل ۶ ستونی را بارگذاری می‌کند.",
            "type": "object",
            "properties": {
                "statement_number": field("string", "شماره صورت‌وضعیت"),
                "work_period": field("string", "دوره کارکرد"),
                "statement_file": field("object", "فایل صورت‌وضعیت"),
                "attendance_18_column_file": field("object", "فایل ۱۸ ستونی"),
                "statement_6_column_file": field("object", "فایل ۶ ستونی"),
            },
            "required": [
                "statement_number",
                "work_period",
                "statement_file",
                "attendance_18_column_file",
                "statement_6_column_file",
            ],
        },
    },
    {
        "order": 6,
        "name": "محاسبه خودکار صورت‌وضعیت",
        "role": "FINANCE_OFFICER",
        "form_type": "AUTO_STATEMENT_CALCULATION",
        "schema": {
            "title": "محاسبه خودکار صورت‌وضعیت",
            "type": "object",
            "properties": {
                "gross_pay": field("number", "مبلغ ناخالص", readOnly=True),
                "base_pay": field("number", "حقوق کارکرد", readOnly=True),
                "overtime_pay": field("number", "اضافه‌کار", readOnly=True),
                "allowances_total": field("number", "جمع مزایا", readOnly=True),
            },
        },
    },
    {
        "order": 7,
        "name": "اعمال کسورات قانونی",
        "role": "FINANCE_OFFICER",
        "form_type": "LEGAL_DEDUCTIONS",
        "schema": {
            "title": "اعمال کسورات قانونی",
            "type": "object",
            "properties": {
                "tax_percent": field("number", "درصد مالیات"),
                "social_security_percent": field("number", "درصد تامین اجتماعی"),
                "good_performance_guarantee_percent": field("number", "درصد تضمین حسن انجام کار"),
            },
            "required": ["tax_percent", "social_security_percent", "good_performance_guarantee_percent"],
        },
    },
    {
        "order": 8,
        "name": "تایید ناظر عملیاتی",
        "role": "OPERATIONAL_MANAGER",
        "form_type": "OPERATIONAL_APPROVAL",
        "schema": {
            "title": "تایید ناظر عملیاتی",
            "type": "object",
            "properties": {
                "approval_remarks": field("string", "توضیحات تایید", widget="textarea"),
            },
            "required": ["approval_remarks"],
        },
    },
    {
        "order": 9,
        "name": "ممیزی نهایی و کنترل بودجه",
        "role": "FINANCE_MANAGER",
        "form_type": "FINAL_BUDGET_AUDIT",
        "schema": {
            "title": "ممیزی نهایی و کنترل بودجه",
            "type": "object",
            "properties": {
                "yekta_balance_checked": field("boolean", "کنترل مانده کد یکتا انجام شد"),
                "budget_approval": field("boolean", "بودجه نهایی تایید شد"),
                "audit_remarks": field("string", "توضیحات ممیزی", widget="textarea"),
            },
            "required": ["yekta_balance_checked", "budget_approval"],
        },
    },
    {
        "order": 10,
        "name": "خروجی خزانه و پرداخت",
        "role": "TREASURY",
        "form_type": "TREASURY_PAYMENT_EXPORT",
        "schema": {
            "title": "خروجی خزانه و پرداخت",
            "type": "object",
            "properties": {
                "payment_date": field("string", "تاریخ پرداخت", format="date"),
                "tracking_number": field("string", "شماره رهگیری خزانه"),
            },
            "required": ["payment_date", "tracking_number"],
        },
    },
]


STEP_BLUEPRINTS = [
    {
        "order": 1,
        "name": "HR Initialization",
        "role": "HR_ADMIN",
        "form_type": "VOLUME_CONTRACT_BASE",
        "schema": {
            "title": "Volume contract base",
            "type": "object",
            "properties": {
                "contract_title": field("string", "Contract title"),
                "contractor_name": field("string", "Contractor name"),
                "total_amount": field("number", "Total amount"),
                "start_date": field("string", "Start date", format="date"),
                "end_date": field("string", "End date", format="date"),
                "contract_category": field("string", "Contract category"),
            },
            "required": ["contract_title", "contractor_name", "total_amount", "start_date", "end_date"],
        },
    },
    {
        "order": 2,
        "name": "Contractor Upload",
        "role": "CONTRACTOR",
        "approval_role": None,
        "form_type": "CONTRACTOR_STATEMENT_UPLOAD",
        "schema": {
            "title": "Contractor statement upload",
            "type": "object",
            "properties": {
                "statement_number": field("string", "Statement number"),
                "work_period": field("string", "Work period"),
                "statement_total_amount": field("number", "Gross statement amount"),
                "statement_file": field("object", "Statement file"),
                "statement_6_column_file": field("object", "6-column Excel"),
                "vat_invoice_files": field("array", "VAT invoice files"),
            },
            "required": ["statement_number", "work_period", "statement_file", "statement_6_column_file"],
        },
    },
    {
        "order": 3,
        "name": "Bahadori Yekta Sub-Process",
        "role": "YEKTA_ADMIN",
        "form_type": "YEKTA_CODE_ISSUANCE",
        "schema": {
            "title": "Yekta code issuance",
            "type": "object",
            "properties": {
                "zone_id": field("integer", "Zone"),
                "department_id": field("integer", "Department"),
                "section_id": field("integer", "Section"),
                "budget_item_id": field("integer", "Budget item"),
                "budget_code": field("string", "Budget code"),
                "cost_center_code": field("string", "Cost center"),
                "continuous_activity_code": field("string", "Continuous action"),
                "special_activity": field("string", "Special activity"),
                "beneficiary_name": field("string", "Beneficiary"),
                "financial_event_defaults": field("object", "Financial event defaults"),
                "event_overrides": field("array", "Per-event overrides"),
                "fiscal_year": field("string", "Fiscal year"),
            },
            "required": [
                "zone_id",
                "department_id",
                "section_id",
                "budget_code",
                "cost_center_code",
                "continuous_activity_code",
                "special_activity",
                "beneficiary_name",
                "financial_event_defaults",
                "fiscal_year",
            ],
        },
    },
    {
        "order": 4,
        "name": "Automated Matrix/Yekta Generation",
        "role": "FINANCE_MANAGER",
        "approval_role": None,
        "form_type": "AUTO_STATEMENT_CALCULATION",
        "schema": {
            "title": "Generated matrix and Yekta codes",
            "type": "object",
            "properties": {
                "gross_amount": field("number", "Gross amount", readOnly=True),
                "financial_events": field("array", "Generated financial events", readOnly=True),
            },
        },
    },
]


def ensure_support_schema(db: Session) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS workflow_definitions (
                id SERIAL PRIMARY KEY,
                code VARCHAR(64) NOT NULL UNIQUE,
                name VARCHAR(255) NOT NULL,
                description TEXT NULL,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
    )
    db.execute(
        text(
            """
            ALTER TABLE workflow_step_definitions
            ADD COLUMN IF NOT EXISTS workflow_definition_id INTEGER NULL
            """
        )
    )
    db.execute(
        text(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'fk_workflow_step_definitions_workflow_definition_id'
                ) THEN
                    ALTER TABLE workflow_step_definitions
                    ADD CONSTRAINT fk_workflow_step_definitions_workflow_definition_id
                    FOREIGN KEY (workflow_definition_id)
                    REFERENCES workflow_definitions(id)
                    ON DELETE SET NULL;
                END IF;
            END $$;
            """
        )
    )
    db.execute(
        text(
            """
            ALTER TABLE workflow_transitions
            ADD COLUMN IF NOT EXISTS action VARCHAR(64) NULL
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS volume_contract_categories (
                id SERIAL PRIMARY KEY,
                category_name VARCHAR(255) NOT NULL UNIQUE,
                workflow_definition_id INTEGER NOT NULL REFERENCES workflow_definitions(id) ON DELETE CASCADE,
                initial_step_id INTEGER NOT NULL REFERENCES workflow_steps(id) ON DELETE RESTRICT,
                sidebar_path VARCHAR(512) NOT NULL,
                workflow_start_path VARCHAR(512) NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
    )
    db.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS ix_volume_contract_categories_workflow_definition_id
            ON volume_contract_categories(workflow_definition_id)
            """
        )
    )


def upsert_workflow_definition(db: Session) -> int:
    row = db.execute(
        text(
            """
            INSERT INTO workflow_definitions (code, name, description, is_active, updated_at)
            VALUES (:code, :name, :description, TRUE, now())
            ON CONFLICT (code) DO UPDATE
            SET name = EXCLUDED.name,
                description = EXCLUDED.description,
                is_active = TRUE,
                updated_at = now()
            RETURNING id
            """
        ),
        {
            "code": WORKFLOW_CODE,
            "name": WORKFLOW_NAME,
            "description": "گردش کار مستقل قراردادهای حجمی، دیجیتالی‌سازی پیوست ۵، اتصال ماتریس مالی و صدور کد یکتا.",
        },
    ).one()
    return int(row.id)


def phase_for_order(order: int) -> int:
    if order <= 3:
        return 1
    if order <= 6:
        return 2
    if order <= 9:
        return 3
    return 4


def upsert_step_definition(db: Session, workflow_definition_id: int, blueprint: dict[str, object]) -> WorkflowStepDefinition:
    step_number = STEP_OFFSET + int(blueprint["order"])
    definition = (
        db.query(WorkflowStepDefinition)
        .filter(WorkflowStepDefinition.step_number == step_number)
        .first()
    )
    if definition is None:
        definition = WorkflowStepDefinition(
            step_number=step_number,
            name=str(blueprint["name"]),
            role_required=str(blueprint["role"]),
            required_form_type=str(blueprint["form_type"]),
            financial_gate=blueprint.get("financial_gate"),
            form_schema=blueprint["schema"],
        )
        db.add(definition)
        db.flush()
    else:
        definition.name = str(blueprint["name"])
        definition.role_required = str(blueprint["role"])
        definition.required_form_type = str(blueprint["form_type"])
        definition.financial_gate = blueprint.get("financial_gate")
        definition.form_schema = blueprint["schema"]
        db.flush()
    db.execute(
        text(
            """
            UPDATE workflow_step_definitions
            SET workflow_definition_id = :workflow_definition_id
            WHERE id = :definition_id
            """
        ),
        {"workflow_definition_id": workflow_definition_id, "definition_id": definition.id},
    )
    return definition


def upsert_workflow_step(db: Session, definition: WorkflowStepDefinition, order: int) -> WorkflowStep:
    order_index = STEP_OFFSET + order
    code = f"VOLUME_CONTRACT_STEP_{order:02d}"
    step = db.query(WorkflowStep).filter(WorkflowStep.code == code).first()
    if step is None:
        step = WorkflowStep(
            code=code,
            name=definition.name,
            phase_number=phase_for_order(order),
            order_index=order_index,
            step_definition_id=definition.id,
        )
        db.add(step)
        db.flush()
    else:
        step.code = code
        step.name = definition.name
        step.phase_number = phase_for_order(order)
        step.order_index = order_index
        step.step_definition_id = definition.id
    return step


def ensure_step_action(db: Session, definition: WorkflowStepDefinition, role: str) -> None:
    if not role:
        db.query(StepAction).filter(
            StepAction.step_definition_id == definition.id,
        ).delete(synchronize_session=False)
        return

    db.query(StepAction).filter(
        StepAction.step_definition_id == definition.id,
        StepAction.assigned_role != role,
    ).delete(synchronize_session=False)

    action = (
        db.query(StepAction)
        .filter(
            StepAction.step_definition_id == definition.id,
            StepAction.assigned_role == role,
        )
        .first()
    )
    if action is None:
        action = StepAction(step_definition_id=definition.id, assigned_role=role)
        db.add(action)
    action.is_required = True
    action.order_index = 1


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
    if transition is None:
        transition = WorkflowTransition(
            from_step_id=from_step.id,
            to_step_id=to_step.id,
            required_role=None,
            is_automatic=False,
        )
        db.add(transition)
        db.flush()

    transition.is_automatic = False
    db.execute(
        text("UPDATE workflow_transitions SET action = 'APPROVE' WHERE id = :transition_id"),
        {"transition_id": transition.id},
    )


def upsert_category_links(db: Session, workflow_definition_id: int, initial_step: WorkflowStep) -> None:
    for category in VOLUME_CONTRACT_CATEGORIES:
        sidebar_path = f"/volume-contracts/dashboard?category={category}"
        workflow_start_path = f"/volume-contracts/workflow/start?category={category}"
        db.execute(
            text(
                """
                INSERT INTO volume_contract_categories (
                    category_name,
                    workflow_definition_id,
                    initial_step_id,
                    sidebar_path,
                    workflow_start_path,
                    is_active,
                    updated_at
                )
                VALUES (
                    :category_name,
                    :workflow_definition_id,
                    :initial_step_id,
                    :sidebar_path,
                    :workflow_start_path,
                    TRUE,
                    now()
                )
                ON CONFLICT (category_name) DO UPDATE
                SET workflow_definition_id = EXCLUDED.workflow_definition_id,
                    initial_step_id = EXCLUDED.initial_step_id,
                    sidebar_path = EXCLUDED.sidebar_path,
                    workflow_start_path = EXCLUDED.workflow_start_path,
                    is_active = TRUE,
                    updated_at = now()
                """
            ),
            {
                "category_name": category,
                "workflow_definition_id": workflow_definition_id,
                "initial_step_id": initial_step.id,
                "sidebar_path": sidebar_path,
                "workflow_start_path": workflow_start_path,
            },
        )


def seed_contractor_project(db: Session, initial_step: WorkflowStep) -> dict[str, object]:
    """Create a demo volume-contract project assigned to the 'contractor' test user."""
    from app.models import CivilProject  # noqa: PLC0415
    from app.models.users import User  # noqa: PLC0415

    contractor_user = db.query(User).filter(User.username == "contractor").first()
    if contractor_user is None:
        print("[seed] Warning: 'contractor' user not found — skipping project assignment.")
        return {"skipped": True}

    # Ensure at least one org_unit and activity exist
    org_unit_id = db.execute(text("SELECT id FROM org_units LIMIT 1")).scalar()
    activity_id = db.execute(text("SELECT id FROM activities LIMIT 1")).scalar()
    if org_unit_id is None or activity_id is None:
        print("[seed] Warning: No org_unit or activity found — skipping demo project creation.")
        return {"skipped": True}

    project_code = "VC-DEMO-CONTRACTOR-001"
    existing = db.query(CivilProject).filter(CivilProject.project_code == project_code).first()
    if existing is None:
        project = CivilProject(
            project_code=project_code,
            title="قرارداد آزمایشی پیمانکار - نظافت و پذیرایی",
            contract_category=VOLUME_CONTRACT_CATEGORIES[0],
            owning_org_unit_id=org_unit_id,
            activity_id=activity_id,
            current_step_id=initial_step.id,
            contractor_id=contractor_user.id,
            is_active=True,
        )
        db.add(project)
        db.flush()
        print(f"[seed] Created demo project '{project_code}' assigned to contractor user id={contractor_user.id}.")
        return {"project_code": project_code, "contractor_id": contractor_user.id}
    else:
        existing.contractor_id = contractor_user.id
        existing.current_step_id = initial_step.id
        db.flush()
        print(f"[seed] Updated existing project '{project_code}' -> contractor_id={contractor_user.id}.")
        return {"project_code": project_code, "contractor_id": contractor_user.id, "updated": True}


def seed() -> dict[str, object]:
    db = SessionLocal()
    try:
        ensure_support_schema(db)
        workflow_definition_id = upsert_workflow_definition(db)

        steps: dict[int, WorkflowStep] = {}
        definitions: dict[int, WorkflowStepDefinition] = {}
        for blueprint in STEP_BLUEPRINTS:
            order = int(blueprint["order"])
            definition = upsert_step_definition(db, workflow_definition_id, blueprint)
            step = upsert_workflow_step(db, definition, order)
            approval_role = blueprint.get("approval_role", blueprint["role"])
            ensure_step_action(db, definition, str(approval_role or ""))
            definitions[order] = definition
            steps[order] = step

        db.flush()
        db.query(WorkflowTransition).filter(
            WorkflowTransition.from_step_id.in_([step.id for step in steps.values()])
        ).delete(synchronize_session=False)
        db.flush()

        for order in range(1, len(STEP_BLUEPRINTS)):
            ensure_transition(db, steps[order], steps[order + 1])

        upsert_category_links(db, workflow_definition_id, steps[1])

        # Seed a demo project assigned to the contractor test user at Step 102.
        contractor_project = seed_contractor_project(db, steps[2])

        db.commit()

        return {
            "workflow_definition_id": workflow_definition_id,
            "workflow_code": WORKFLOW_CODE,
            "step_ids": {order: step.id for order, step in steps.items()},
            "step_definition_ids": {order: definition.id for order, definition in definitions.items()},
            "categories": VOLUME_CONTRACT_CATEGORIES,
            "contractor_demo_project": contractor_project,
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    result = seed()
    print(json.dumps(result, ensure_ascii=False, indent=2))

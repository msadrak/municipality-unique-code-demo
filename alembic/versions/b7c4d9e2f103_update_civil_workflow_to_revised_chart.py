"""update civil workflow to revised 39-step chart

Revision ID: b7c4d9e2f103
Revises: 0eef78241279
Create Date: 2026-04-28 12:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "b7c4d9e2f103"
down_revision: Union[str, None] = "0eef78241279"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


workflow_step_definitions = sa.table(
    "workflow_step_definitions",
    sa.column("id", sa.Integer),
    sa.column("step_number", sa.Integer),
    sa.column("name", sa.String),
    sa.column("role_required", sa.String),
    sa.column("required_form_type", sa.String),
    sa.column("form_schema", sa.JSON),
    sa.column("financial_gate", sa.String),
)

workflow_steps = sa.table(
    "workflow_steps",
    sa.column("id", sa.Integer),
    sa.column("code", sa.String),
    sa.column("name", sa.String),
    sa.column("phase_number", sa.Integer),
    sa.column("order_index", sa.Integer),
    sa.column("step_definition_id", sa.Integer),
)

workflow_transitions = sa.table(
    "workflow_transitions",
    sa.column("from_step_id", sa.Integer),
    sa.column("to_step_id", sa.Integer),
    sa.column("required_role", sa.String),
    sa.column("is_automatic", sa.Boolean),
)

step_actions = sa.table(
    "step_actions",
    sa.column("step_definition_id", sa.Integer),
    sa.column("assigned_role", sa.String),
    sa.column("is_required", sa.Boolean),
    sa.column("order_index", sa.Integer),
)


PROGRESS_STATEMENT_SCHEMA = {
    "title": "فرم صورت وضعیت قطعی و تعدیل قطعی",
    "type": "object",
    "properties": {
        "invoice_number": {"type": "string", "title": "شماره صورت وضعیت"},
        "period": {"type": "string", "title": "دوره کارکرد"},
        "gross_amount": {"type": "number", "title": "مبلغ ناخالص"},
        "contractor_name": {"type": "string", "title": "نام پیمانکار"},
        "contract_number": {"type": "string", "title": "شماره قرارداد"},
        "description": {"type": "string", "title": "شرح عملیات", "widget": "textarea"},
    },
    "required": ["invoice_number", "period", "gross_amount", "contractor_name", "contract_number"],
}

CONTRACTOR_ASSIGNMENT_SCHEMA = {
    "title": "تعیین پیمانکار برنده",
    "description": "اطلاعات هویتی و مالی پیمانکار برنده را همراه با صورتجلسه کمیسیون ثبت کنید.",
    "type": "object",
    "properties": {
        "contractor_name": {"type": "string", "title": "نام پیمانکار"},
        "national_id": {"type": "string", "title": "کد ملی / شناسه حقوقی"},
        "phone_number": {"type": "string", "title": "شماره موبایل"},
        "winning_bid": {"type": "number", "title": "مبلغ پیشنهادی برنده - ریال"},
        "contract_coefficient": {"type": "number", "title": "ضریب پیمان"},
    },
    "required": [
        "contractor_name",
        "national_id",
        "phone_number",
        "winning_bid",
        "contract_coefficient",
    ],
}

PHASE_1_STEP_1_SCHEMA = {
    "title": "تعریف پروژه برای سال آینده",
    "description": "فقط اطلاعات پایه را وارد کنید و مدارک فنی، فرم‌های طراحی و مستندات تفصیلی را در بخش پیوست‌ها بارگذاری کنید.",
    "type": "object",
    "properties": {
        "project_title": {"type": "string", "title": "عنوان پروژه"},
        "reference_number": {"type": "string", "title": "شماره نامه / ارجاع"},
    },
    "required": ["project_title", "reference_number"],
}

TEMPORARY_HANDOVER_SCHEMA = {
    "title": "صورتجلسه تحویل موقت و امضاها",
    "type": "object",
    "additionalProperties": True,
    "properties": {
        "meeting_date": {"type": "string", "title": "تاریخ جلسه"},
        "commission_members": {"type": "string", "title": "اعضای کمیسیون", "widget": "textarea"},
        "decisions": {"type": "string", "title": "مصوبات", "widget": "textarea"},
    },
}

FINAL_HANDOVER_SCHEMA = {
    "title": "صورتجلسه تحویل قطعی",
    "type": "object",
    "additionalProperties": True,
    "properties": {
        "handover_date": {"type": "string", "title": "تاریخ تحویل قطعی"},
        "commission_members": {"type": "string", "title": "اعضای کمیسیون", "widget": "textarea"},
        "final_decision": {"type": "string", "title": "نتیجه نهایی", "widget": "textarea"},
    },
}

SMART_FORM_SCHEMAS = {
    1: PHASE_1_STEP_1_SCHEMA,
    15: CONTRACTOR_ASSIGNMENT_SCHEMA,
    30: TEMPORARY_HANDOVER_SCHEMA,
    33: PROGRESS_STATEMENT_SCHEMA,
    38: FINAL_HANDOVER_SCHEMA,
}

STEP_BLUEPRINTS = (
    (1, "تعریف پروژه برای سال آینده...", "CIVIL_MANAGER", "NEXT_YEAR_PROJECT_DEFINITION", None),
    (2, "تصویب بودجه شورا", "FINANCE_MANAGER", "COUNCIL_BUDGET_APPROVAL", "BUDGET_BLOCKED"),
    (3, "تخمین ریالی هزینه انجام", "CIVIL_MANAGER", "COST_ESTIMATE", None),
    (4, "ثبت در سامانه های مربوطه...", "CIVIL_MANAGER", "SYSTEM_REGISTRATION", None),
    (5, "ارسال به سازمان طراحی...", "CIVIL_MANAGER", "DESIGN_ORG_REFERRAL", None),
    (6, "برگزاری جلسات کمیته فنی فاز 1", "CIVIL_MANAGER", "TECHNICAL_COMMITTEE_PHASE_1", None),
    (7, "برگزاری جلسات اولویت بندی زمان طراحی", "CIVIL_MANAGER", "DESIGN_PRIORITY_MEETING", None),
    (8, "تهیه فرم های مستندسازی...", "CIVIL_MANAGER", "DOCUMENTATION_FORMS", None),
    (9, "تکمیل اطلاعات درخواستی طراحی...", "CIVIL_MANAGER", "DESIGN_REQUEST_COMPLETION", None),
    (10, "برگزاری جلسات کمیته فنی فاز 2", "CIVIL_MANAGER", "TECHNICAL_COMMITTEE_PHASE_2", None),
    (11, "بررسی طرح توسط کارشناسان معاونت عمران", "CIVIL_MANAGER", "DEPUTY_TECHNICAL_REVIEW", None),
    (12, "با توجه به مبلغ برآورد: صورت استعلام/مناقصه", "TENDERING_OFFICER", "PROCUREMENT_METHOD_DECISION", None),
    (13, "مرحله 10 - در انتظار تعیین کارفرما", "CIVIL_MANAGER", None, None),
    (14, "دعوتنامه شرکت در کمیسیون", "TENDERING_OFFICER", "COMMISSION_INVITATION", None),
    (15, "شرکت در جلسه کمیسیون و تعیین برنده", "TENDERING_OFFICER", "CONTRACTOR_ASSIGNMENT", None),
    (16, "دعوتنامه برای پیمانکار برنده", "CONTRACTS_OFFICER", "WINNING_CONTRACTOR_INVITATION", None),
    (17, "تهیه قرارداد و امضاء مسئولین", "CONTRACTS_OFFICER", "CONTRACT_SIGNED", "CONTRACT_COMMITTED"),
    (18, "ابلاغ قرارداد به پیمانکار", "CONTRACTS_OFFICER", "CONTRACT_NOTICE_TO_CONTRACTOR", None),
    (19, "ابلاغ ناظر به پیمانکار", "CIVIL_MANAGER", "SUPERVISOR_NOTICE_TO_CONTRACTOR", None),
    (20, "دعوتنامه تحویل زمین", "DELIVERY_COMMISSION", "LAND_HANDOVER_INVITATION", None),
    (21, "صورتجلسه تحویل زمین", "DELIVERY_COMMISSION", "LAND_HANDOVER", None),
    (22, "ابلاغ تحویل زمین", "CONTRACTS_OFFICER", "LAND_HANDOVER_NOTICE", None),
    (23, "ارائه صورتوضعیت پیمانکار به ناظر", "CONTRACTOR", "CONTRACTOR_PROGRESS_STATEMENT", None),
    (24, "تهیه روکش توسط کارشناس پیمان", "CONTRACTS_OFFICER", "CONTRACT_COVER_SHEET", None),
    (25, "تکمیل امضا، و شماره شدن روکش", "CONTRACTS_OFFICER", "COVER_SHEET_SIGNATURES", None),
    (26, "واحد رسیدگی مجدد", "FINANCE_MANAGER", "REVIEW_UNIT_RECHECK", None),
    (27, "درخواست تحویل موقت", "CONTRACTOR", "TEMPORARY_HANDOVER_REQUEST", None),
    (28, "درخواست سیستمی از منطقه به معاونت", "CIVIL_MANAGER", "REGION_TO_DEPUTY_REQUEST", None),
    (29, "دعوتنامه تحویل موقت", "DELIVERY_COMMISSION", "TEMPORARY_HANDOVER_INVITATION", None),
    (30, "صورتجلسه تحویل موقت و امضاها (هوشمند)", "DELIVERY_COMMISSION", "TEMPORARY_HANDOVER_MINUTES", None),
    (31, "ابلاغ تحویل موقت و آزادسازی ضمانتنامه", "FINANCE_MANAGER", "TEMPORARY_HANDOVER_NOTICE_GUARANTEE_RELEASE", "GUARANTEE_RELEASED"),
    (32, "ارسال اطلاعات مالی مناطق", "FINANCE_MANAGER", "REGIONAL_FINANCIAL_DATA", None),
    (33, "صورت وضعیت قطعی و تعدیل قطعی (هوشمند)", "FINANCE_MANAGER", "PROGRESS_STATEMENT", "TRANSACTION_CREATED"),
    (34, "ابلاغ 25% مازاد بر قرارداد", "CONTRACTS_OFFICER", "CONTRACT_SURPLUS_25_NOTICE", None),
    (35, "درخواست تحویل قطعی پیمانکار", "CONTRACTOR", "FINAL_HANDOVER_REQUEST", None),
    (36, "درخواست سیستمی جهت معاونت جهت تایید", "CIVIL_MANAGER", "FINAL_HANDOVER_DEPUTY_APPROVAL_REQUEST", None),
    (37, "دعوتنامه تحویل قطعی", "DELIVERY_COMMISSION", "FINAL_HANDOVER_INVITATION", None),
    (38, "صورتجلسه تحویل قطعی (هوشمند)", "DELIVERY_COMMISSION", "FINAL_HANDOVER_MINUTES", None),
    (39, "ابلاغ تحویل قطعی", "CONTRACTS_OFFICER", "FINAL_HANDOVER_NOTICE", None),
)


def phase_for_step(step_number: int) -> int:
    if step_number <= 11:
        return 1
    if step_number <= 18:
        return 2
    if step_number <= 34:
        return 3
    return 4


def _scalar(connection: sa.Connection, statement: sa.sql.Select) -> int | None:
    return connection.execute(statement).scalar_one_or_none()


def upgrade() -> None:
    connection = op.get_bind()
    step_ids: dict[int, int] = {}
    definition_ids: dict[int, int] = {}

    for step_number, name, role_required, required_form_type, financial_gate in STEP_BLUEPRINTS:
        form_schema = SMART_FORM_SCHEMAS.get(step_number)
        definition_id = _scalar(
            connection,
            sa.select(workflow_step_definitions.c.id).where(
                workflow_step_definitions.c.step_number == step_number
            ),
        )
        definition_values = {
            "step_number": step_number,
            "name": name,
            "role_required": role_required,
            "required_form_type": required_form_type,
            "form_schema": form_schema,
            "financial_gate": financial_gate,
        }
        if definition_id is None:
            definition_id = connection.execute(
                workflow_step_definitions.insert()
                .values(**definition_values)
                .returning(workflow_step_definitions.c.id)
            ).scalar_one()
        else:
            connection.execute(
                workflow_step_definitions.update()
                .where(workflow_step_definitions.c.id == definition_id)
                .values(**definition_values)
            )
        definition_ids[step_number] = definition_id

        step_id = _scalar(
            connection,
            sa.select(workflow_steps.c.id).where(workflow_steps.c.order_index == step_number),
        )
        step_values = {
            "code": f"CIVIL_STEP_{step_number:02d}",
            "name": name,
            "phase_number": phase_for_step(step_number),
            "order_index": step_number,
            "step_definition_id": definition_id,
        }
        if step_id is None:
            step_id = connection.execute(
                workflow_steps.insert()
                .values(**step_values)
                .returning(workflow_steps.c.id)
            ).scalar_one()
        else:
            connection.execute(
                workflow_steps.update()
                .where(workflow_steps.c.id == step_id)
                .values(**step_values)
            )
        step_ids[step_number] = step_id

    connection.execute(
        workflow_transitions.delete().where(
            workflow_transitions.c.from_step_id.in_(list(step_ids.values()))
        )
    )
    for step_number in range(1, len(STEP_BLUEPRINTS)):
        connection.execute(
            workflow_transitions.insert().values(
                from_step_id=step_ids[step_number],
                to_step_id=step_ids[step_number + 1],
                required_role=None,
                is_automatic=False,
            )
        )

    step33_definition_id = definition_ids[33]
    connection.execute(
        step_actions.delete().where(
            sa.and_(
                step_actions.c.step_definition_id == step33_definition_id,
                step_actions.c.assigned_role == "FINANCE_MANAGER",
            )
        )
    )
    connection.execute(
        step_actions.insert().values(
            step_definition_id=step33_definition_id,
            assigned_role="FINANCE_MANAGER",
            is_required=True,
            order_index=1,
        )
    )


def downgrade() -> None:
    connection = op.get_bind()
    ids_to_remove = connection.execute(
        sa.select(workflow_steps.c.id).where(workflow_steps.c.order_index > 31)
    ).scalars().all()
    if ids_to_remove:
        connection.execute(
            workflow_transitions.delete().where(
                sa.or_(
                    workflow_transitions.c.from_step_id.in_(ids_to_remove),
                    workflow_transitions.c.to_step_id.in_(ids_to_remove),
                )
            )
        )
        connection.execute(workflow_steps.delete().where(workflow_steps.c.id.in_(ids_to_remove)))

    definition_ids_to_remove = connection.execute(
        sa.select(workflow_step_definitions.c.id).where(
            workflow_step_definitions.c.step_number > 31
        )
    ).scalars().all()
    if definition_ids_to_remove:
        connection.execute(
            step_actions.delete().where(
                step_actions.c.step_definition_id.in_(definition_ids_to_remove)
            )
        )
        connection.execute(
            workflow_step_definitions.delete().where(
                workflow_step_definitions.c.id.in_(definition_ids_to_remove)
            )
        )

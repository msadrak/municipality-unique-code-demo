"""add civil workflow blueprint definitions

Revision ID: 7ead37f8eaa7
Revises: e5dd22a96fca
Create Date: 2026-04-26 19:57:07.366571

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7ead37f8eaa7"
down_revision: Union[str, None] = "e5dd22a96fca"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


workflow_step_definitions = sa.table(
    "workflow_step_definitions",
    sa.column("step_number", sa.Integer),
    sa.column("name", sa.String),
    sa.column("role_required", sa.String),
    sa.column("required_form_type", sa.String),
    sa.column("financial_gate", sa.String),
)


STEP_DEFINITIONS = [
    (1, "ثبت درخواست پروژه", "CIVIL_MANAGER", "PROJECT_REQUEST", None),
    (2, "بررسی اولیه درخواست", "CIVIL_MANAGER", "PRELIMINARY_REVIEW", None),
    (3, "بازدید و برداشت میدانی", "SUPERVISOR", "SITE_SURVEY_REPORT", None),
    (4, "برآورد اولیه و ریزمتره", "SUPERVISOR", "ESTIMATE_SHEET", None),
    (5, "تحویل زمین", "DELIVERY_COMMISSION", "LAND_HANDOVER", None),
    (6, "تهیه مدارک طراحی", "CIVIL_MANAGER", "DESIGN_PACKAGE", None),
    (7, "تایید فنی نقشه ها", "CIVIL_MANAGER", "TECHNICAL_APPROVAL", None),
    (8, "مسدودسازی اعتبار", "FINANCE_MANAGER", "BUDGET_BLOCK_REQUEST", "BUDGET_BLOCKED"),
    (9, "تهیه اسناد مناقصه", "TENDERING_OFFICER", "TENDER_PACKAGE", None),
    (10, "انتشار فراخوان مناقصه", "TENDERING_OFFICER", "TENDER_NOTICE", None),
    (11, "صورتجلسه بازگشایی پاکات", "TENDERING_OFFICER", "BID_OPENING_MINUTES", None),
    (12, "ارزیابی پیشنهادها", "TENDERING_OFFICER", "BID_EVALUATION_REPORT", None),
    (13, "ابلاغ برنده مناقصه", "CIVIL_MANAGER", "WINNER_APPROVAL", None),
    (14, "تنظیم پیش نویس قرارداد", "CONTRACTS_OFFICER", "CONTRACT_DRAFT", None),
    (15, "تعهد قرارداد", "CONTRACTS_OFFICER", "CONTRACT_SIGNED", "CONTRACT_COMMITTED"),
    (16, "تحویل کارگاه به پیمانکار", "DELIVERY_COMMISSION", "SITE_MOBILIZATION", None),
    (17, "تعیین ناظر مقیم", "CIVIL_MANAGER", "SUPERVISOR_ASSIGNMENT", None),
    (18, "ابلاغ دستور شروع کار", "CONTRACTS_OFFICER", "START_ORDER", None),
    (19, "ثبت گزارش روزانه عملیات", "SUPERVISOR", "DAILY_REPORT", None),
    (20, "تهیه صورت وضعیت", "SUPERVISOR", "PROGRESS_STATEMENT", None),
    (21, "ایجاد سند مالی", "FINANCE_MANAGER", "PAYMENT_REQUEST", "TRANSACTION_CREATED"),
    (22, "کنترل و تایید مالی", "FINANCE_MANAGER", "FINANCE_REVIEW", None),
    (23, "استعلام و تایید حراست", "SECURITY", "SECURITY_CLEARANCE", None),
    (24, "تایید شهردار", "MAYOR", "MAYOR_APPROVAL", "PAYMENT_APPROVED"),
    (25, "صدور دستور پرداخت", "FINANCE_MANAGER", "PAYMENT_ORDER", None),
    (26, "گزارش اتمام عملیات", "SUPERVISOR", "COMPLETION_REPORT", None),
    (27, "صورتجلسه کمیسیون", "DELIVERY_COMMISSION", "COMMISSION_MINUTES", None),
    (28, "تحویل موقت پروژه", "DELIVERY_COMMISSION", "TEMPORARY_HANDOVER", None),
    (29, "دوره رفع نقص", "SUPERVISOR", "DEFECTS_LIABILITY_REPORT", None),
    (30, "آزادسازی تضمین ها", "FINANCE_MANAGER", "GUARANTEE_RELEASE", "GUARANTEE_RELEASED"),
    (31, "اختتام و بایگانی پرونده", "CIVIL_MANAGER", "CLOSEOUT_ARCHIVE", None),
]


def upgrade() -> None:
    op.create_table(
        "workflow_step_definitions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("step_number", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("role_required", sa.String(length=64), nullable=True),
        sa.Column("required_form_type", sa.String(length=128), nullable=True),
        sa.Column("financial_gate", sa.String(length=128), nullable=True),
        sa.CheckConstraint("step_number >= 1", name="ck_workflow_step_definitions_step_number_positive"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("step_number", name="uq_workflow_step_definitions_step_number"),
    )
    op.create_index(op.f("ix_workflow_step_definitions_financial_gate"), "workflow_step_definitions", ["financial_gate"], unique=False)
    op.create_index(op.f("ix_workflow_step_definitions_id"), "workflow_step_definitions", ["id"], unique=False)
    op.create_index(op.f("ix_workflow_step_definitions_required_form_type"), "workflow_step_definitions", ["required_form_type"], unique=False)
    op.create_index(op.f("ix_workflow_step_definitions_role_required"), "workflow_step_definitions", ["role_required"], unique=False)
    op.create_index(op.f("ix_workflow_step_definitions_step_number"), "workflow_step_definitions", ["step_number"], unique=False)

    op.bulk_insert(
        workflow_step_definitions,
        [
            {
                "step_number": step_number,
                "name": name,
                "role_required": role_required,
                "required_form_type": required_form_type,
                "financial_gate": financial_gate,
            }
            for step_number, name, role_required, required_form_type, financial_gate in STEP_DEFINITIONS
        ],
    )

    op.create_table(
        "step_actions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("step_definition_id", sa.Integer(), nullable=False),
        sa.Column("assigned_role", sa.String(length=64), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["step_definition_id"], ["workflow_step_definitions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("step_definition_id", "assigned_role", name="uq_step_actions_definition_role"),
    )
    op.create_index(op.f("ix_step_actions_assigned_role"), "step_actions", ["assigned_role"], unique=False)
    op.create_index(op.f("ix_step_actions_id"), "step_actions", ["id"], unique=False)
    op.create_index(op.f("ix_step_actions_step_definition_id"), "step_actions", ["step_definition_id"], unique=False)

    op.execute(
        """
        INSERT INTO step_actions (step_definition_id, assigned_role, is_required, order_index)
        SELECT definition.id, action.assigned_role, action.is_required, action.order_index
        FROM (
            VALUES
                (8, 'FINANCE_MANAGER', true, 1),
                (13, 'CIVIL_MANAGER', true, 1),
                (15, 'CONTRACTS_OFFICER', true, 1),
                (15, 'FINANCE_MANAGER', true, 2),
                (21, 'SUPERVISOR', true, 1),
                (21, 'FINANCE_MANAGER', true, 2),
                (22, 'FINANCE_MANAGER', true, 1),
                (23, 'SECURITY', true, 1),
                (24, 'MAYOR', true, 1),
                (24, 'FINANCE_MANAGER', true, 2),
                (27, 'DELIVERY_COMMISSION', true, 1),
                (27, 'SECURITY', true, 2),
                (27, 'FINANCE_MANAGER', true, 3),
                (27, 'MAYOR', true, 4),
                (30, 'FINANCE_MANAGER', true, 1)
        ) AS action(step_number, assigned_role, is_required, order_index)
        JOIN workflow_step_definitions AS definition
          ON definition.step_number = action.step_number
        """
    )

    op.add_column("approval_tasks", sa.Column("step_action_id", sa.Integer(), nullable=True))
    op.add_column(
        "approval_tasks",
        sa.Column("is_required", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.alter_column("approval_tasks", "is_required", server_default=None)
    op.create_index(op.f("ix_approval_tasks_step_action_id"), "approval_tasks", ["step_action_id"], unique=False)
    op.create_foreign_key(
        "fk_approval_tasks_step_action_id_step_actions",
        "approval_tasks",
        "step_actions",
        ["step_action_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("workflow_steps", sa.Column("step_definition_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_workflow_steps_step_definition_id"), "workflow_steps", ["step_definition_id"], unique=False)
    op.create_foreign_key(
        "fk_workflow_steps_step_definition_id_definitions",
        "workflow_steps",
        "workflow_step_definitions",
        ["step_definition_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.execute(
        """
        UPDATE workflow_steps AS step
        SET
            step_definition_id = definition.id,
            name = definition.name
        FROM workflow_step_definitions AS definition
        WHERE step.order_index = definition.step_number
        """
    )


def downgrade() -> None:
    op.drop_constraint("fk_workflow_steps_step_definition_id_definitions", "workflow_steps", type_="foreignkey")
    op.drop_index(op.f("ix_workflow_steps_step_definition_id"), table_name="workflow_steps")
    op.drop_column("workflow_steps", "step_definition_id")

    op.drop_constraint("fk_approval_tasks_step_action_id_step_actions", "approval_tasks", type_="foreignkey")
    op.drop_index(op.f("ix_approval_tasks_step_action_id"), table_name="approval_tasks")
    op.drop_column("approval_tasks", "is_required")
    op.drop_column("approval_tasks", "step_action_id")

    op.drop_index(op.f("ix_step_actions_step_definition_id"), table_name="step_actions")
    op.drop_index(op.f("ix_step_actions_id"), table_name="step_actions")
    op.drop_index(op.f("ix_step_actions_assigned_role"), table_name="step_actions")
    op.drop_table("step_actions")

    op.drop_index(op.f("ix_workflow_step_definitions_step_number"), table_name="workflow_step_definitions")
    op.drop_index(op.f("ix_workflow_step_definitions_role_required"), table_name="workflow_step_definitions")
    op.drop_index(op.f("ix_workflow_step_definitions_required_form_type"), table_name="workflow_step_definitions")
    op.drop_index(op.f("ix_workflow_step_definitions_id"), table_name="workflow_step_definitions")
    op.drop_index(op.f("ix_workflow_step_definitions_financial_gate"), table_name="workflow_step_definitions")
    op.drop_table("workflow_step_definitions")

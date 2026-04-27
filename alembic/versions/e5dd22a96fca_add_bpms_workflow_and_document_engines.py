"""add bpms workflow and document engines

Revision ID: e5dd22a96fca
Revises: d1e9b4c2a7f0
Create Date: 2026-04-26 19:19:46.261039

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "e5dd22a96fca"
down_revision: Union[str, None] = "d1e9b4c2a7f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


approval_task_status = postgresql.ENUM(
    "PENDING",
    "APPROVED",
    "REJECTED",
    name="approval_task_status",
)


def upgrade() -> None:
    bind = op.get_bind()
    approval_task_status.create(bind, checkfirst=True)

    op.create_table(
        "workflow_steps",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("phase_number", sa.Integer(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.CheckConstraint("phase_number BETWEEN 1 AND 4", name="ck_workflow_steps_phase_range"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_workflow_steps_code"),
        sa.UniqueConstraint("order_index", name="uq_workflow_steps_order_index"),
    )
    op.create_index(op.f("ix_workflow_steps_code"), "workflow_steps", ["code"], unique=False)
    op.create_index(op.f("ix_workflow_steps_id"), "workflow_steps", ["id"], unique=False)
    op.create_index(op.f("ix_workflow_steps_order_index"), "workflow_steps", ["order_index"], unique=False)
    op.create_index(op.f("ix_workflow_steps_phase_number"), "workflow_steps", ["phase_number"], unique=False)

    op.execute(
        """
        INSERT INTO workflow_steps (code, name, phase_number, order_index)
        SELECT
            'CIVIL_STEP_' || lpad(step_no::text, 2, '0'),
            'Civil workflow step ' || step_no::text,
            CASE
                WHEN step_no <= 8 THEN 1
                WHEN step_no <= 16 THEN 2
                WHEN step_no <= 24 THEN 3
                ELSE 4
            END,
            step_no
        FROM generate_series(1, 31) AS step_no
        """
    )

    op.create_table(
        "workflow_transitions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("from_step_id", sa.Integer(), nullable=False),
        sa.Column("to_step_id", sa.Integer(), nullable=False),
        sa.Column("required_role", sa.String(length=64), nullable=True),
        sa.Column("is_automatic", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["from_step_id"], ["workflow_steps.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["to_step_id"], ["workflow_steps.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("from_step_id", "to_step_id", "required_role", name="uq_workflow_transitions_route"),
    )
    op.create_index(
        op.f("ix_workflow_transitions_from_step_id"),
        "workflow_transitions",
        ["from_step_id"],
        unique=False,
    )
    op.create_index(op.f("ix_workflow_transitions_id"), "workflow_transitions", ["id"], unique=False)
    op.create_index(
        op.f("ix_workflow_transitions_required_role"),
        "workflow_transitions",
        ["required_role"],
        unique=False,
    )
    op.create_index(
        op.f("ix_workflow_transitions_to_step_id"),
        "workflow_transitions",
        ["to_step_id"],
        unique=False,
    )

    op.execute(
        """
        INSERT INTO workflow_transitions (from_step_id, to_step_id, required_role, is_automatic)
        SELECT from_step.id, to_step.id, NULL, false
        FROM workflow_steps AS from_step
        JOIN workflow_steps AS to_step
          ON to_step.order_index = from_step.order_index + 1
        WHERE from_step.order_index BETWEEN 1 AND 30
        """
    )

    op.create_table(
        "entity_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("step_id", sa.Integer(), nullable=False),
        sa.Column("document_type", sa.String(length=128), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("file_path", sa.String(length=1024), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["civil_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["step_id"], ["workflow_steps.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_entity_documents_created_by_id"), "entity_documents", ["created_by_id"], unique=False)
    op.create_index(op.f("ix_entity_documents_document_type"), "entity_documents", ["document_type"], unique=False)
    op.create_index(op.f("ix_entity_documents_id"), "entity_documents", ["id"], unique=False)
    op.create_index(op.f("ix_entity_documents_project_id"), "entity_documents", ["project_id"], unique=False)
    op.create_index(op.f("ix_entity_documents_step_id"), "entity_documents", ["step_id"], unique=False)

    op.create_table(
        "approval_tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("step_id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=True),
        sa.Column("assigned_role", sa.String(length=64), nullable=False),
        sa.Column("assigned_user_id", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "PENDING",
                "APPROVED",
                "REJECTED",
                name="approval_task_status",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["assigned_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["document_id"], ["entity_documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["civil_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["step_id"], ["workflow_steps.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_approval_tasks_assigned_role"), "approval_tasks", ["assigned_role"], unique=False)
    op.create_index(op.f("ix_approval_tasks_assigned_user_id"), "approval_tasks", ["assigned_user_id"], unique=False)
    op.create_index(op.f("ix_approval_tasks_document_id"), "approval_tasks", ["document_id"], unique=False)
    op.create_index(op.f("ix_approval_tasks_id"), "approval_tasks", ["id"], unique=False)
    op.create_index(op.f("ix_approval_tasks_project_id"), "approval_tasks", ["project_id"], unique=False)
    op.create_index(op.f("ix_approval_tasks_status"), "approval_tasks", ["status"], unique=False)
    op.create_index(op.f("ix_approval_tasks_step_id"), "approval_tasks", ["step_id"], unique=False)

    op.add_column("civil_projects", sa.Column("current_step_id", sa.Integer(), nullable=True))
    op.execute(
        """
        UPDATE civil_projects AS project
        SET current_step_id = step.id
        FROM workflow_steps AS step
        WHERE step.order_index = project.current_step
        """
    )
    op.alter_column("civil_projects", "current_step_id", nullable=False)
    op.create_index(op.f("ix_civil_projects_current_step_id"), "civil_projects", ["current_step_id"], unique=False)
    op.create_foreign_key(
        "fk_civil_projects_current_step_id_workflow_steps",
        "civil_projects",
        "workflow_steps",
        ["current_step_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.drop_constraint("ck_civil_projects_phase_range", "civil_projects", type_="check")
    op.drop_constraint("ck_civil_projects_step_range", "civil_projects", type_="check")
    op.drop_column("civil_projects", "current_phase")
    op.drop_column("civil_projects", "current_step")


def downgrade() -> None:
    op.add_column("civil_projects", sa.Column("current_step", sa.Integer(), nullable=True))
    op.add_column("civil_projects", sa.Column("current_phase", sa.Integer(), nullable=True))
    op.execute(
        """
        UPDATE civil_projects AS project
        SET
            current_phase = step.phase_number,
            current_step = step.order_index
        FROM workflow_steps AS step
        WHERE project.current_step_id = step.id
        """
    )
    op.alter_column("civil_projects", "current_phase", nullable=False)
    op.alter_column("civil_projects", "current_step", nullable=False)
    op.create_check_constraint(
        "ck_civil_projects_phase_range",
        "civil_projects",
        "current_phase BETWEEN 1 AND 4",
    )
    op.create_check_constraint(
        "ck_civil_projects_step_range",
        "civil_projects",
        "current_step BETWEEN 1 AND 31",
    )

    op.drop_constraint("fk_civil_projects_current_step_id_workflow_steps", "civil_projects", type_="foreignkey")
    op.drop_index(op.f("ix_civil_projects_current_step_id"), table_name="civil_projects")
    op.drop_column("civil_projects", "current_step_id")

    op.drop_index(op.f("ix_approval_tasks_step_id"), table_name="approval_tasks")
    op.drop_index(op.f("ix_approval_tasks_status"), table_name="approval_tasks")
    op.drop_index(op.f("ix_approval_tasks_project_id"), table_name="approval_tasks")
    op.drop_index(op.f("ix_approval_tasks_id"), table_name="approval_tasks")
    op.drop_index(op.f("ix_approval_tasks_document_id"), table_name="approval_tasks")
    op.drop_index(op.f("ix_approval_tasks_assigned_user_id"), table_name="approval_tasks")
    op.drop_index(op.f("ix_approval_tasks_assigned_role"), table_name="approval_tasks")
    op.drop_table("approval_tasks")

    op.drop_index(op.f("ix_entity_documents_step_id"), table_name="entity_documents")
    op.drop_index(op.f("ix_entity_documents_project_id"), table_name="entity_documents")
    op.drop_index(op.f("ix_entity_documents_id"), table_name="entity_documents")
    op.drop_index(op.f("ix_entity_documents_document_type"), table_name="entity_documents")
    op.drop_index(op.f("ix_entity_documents_created_by_id"), table_name="entity_documents")
    op.drop_table("entity_documents")

    op.drop_index(op.f("ix_workflow_transitions_to_step_id"), table_name="workflow_transitions")
    op.drop_index(op.f("ix_workflow_transitions_required_role"), table_name="workflow_transitions")
    op.drop_index(op.f("ix_workflow_transitions_id"), table_name="workflow_transitions")
    op.drop_index(op.f("ix_workflow_transitions_from_step_id"), table_name="workflow_transitions")
    op.drop_table("workflow_transitions")

    op.drop_index(op.f("ix_workflow_steps_phase_number"), table_name="workflow_steps")
    op.drop_index(op.f("ix_workflow_steps_order_index"), table_name="workflow_steps")
    op.drop_index(op.f("ix_workflow_steps_id"), table_name="workflow_steps")
    op.drop_index(op.f("ix_workflow_steps_code"), table_name="workflow_steps")
    op.drop_table("workflow_steps")

    bind = op.get_bind()
    approval_task_status.drop(bind, checkfirst=True)

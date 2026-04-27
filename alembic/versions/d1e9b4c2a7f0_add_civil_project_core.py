"""add civil project core

Revision ID: d1e9b4c2a7f0
Revises: 52c174e4cdc7, f4d3c7a9b21e
Create Date: 2026-04-25 14:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "d1e9b4c2a7f0"
down_revision: Union[str, Sequence[str], None] = ("52c174e4cdc7", "f4d3c7a9b21e")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


civil_project_role = sa.Enum(
    "CIVIL_MANAGER",
    "TENDERING_OFFICER",
    "CONTRACTS_OFFICER",
    "SUPERVISOR",
    "DELIVERY_COMMISSION",
    "CONTRACTOR",
    "FINANCE_MANAGER",
    name="civil_project_role",
)


def upgrade() -> None:
    bind = op.get_bind()
    civil_project_role.create(bind, checkfirst=True)

    op.create_table(
        "civil_projects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_code", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("owning_org_unit_id", sa.Integer(), nullable=False),
        sa.Column("activity_id", sa.Integer(), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("current_phase", sa.Integer(), nullable=False),
        sa.Column("current_step", sa.Integer(), nullable=False),
        sa.Column("planned_start_date", sa.Date(), nullable=True),
        sa.Column("planned_end_date", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("current_phase BETWEEN 1 AND 4", name="ck_civil_projects_phase_range"),
        sa.CheckConstraint("current_step BETWEEN 1 AND 31", name="ck_civil_projects_step_range"),
        sa.ForeignKeyConstraint(["activity_id"], ["activities.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owning_org_unit_id"], ["org_units.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_code"),
    )
    op.create_index(op.f("ix_civil_projects_activity_id"), "civil_projects", ["activity_id"], unique=False)
    op.create_index(op.f("ix_civil_projects_created_by_id"), "civil_projects", ["created_by_id"], unique=False)
    op.create_index(op.f("ix_civil_projects_id"), "civil_projects", ["id"], unique=False)
    op.create_index(op.f("ix_civil_projects_owning_org_unit_id"), "civil_projects", ["owning_org_unit_id"], unique=False)
    op.create_index(op.f("ix_civil_projects_project_code"), "civil_projects", ["project_code"], unique=True)
    op.create_index(op.f("ix_civil_projects_title"), "civil_projects", ["title"], unique=False)

    op.create_table(
        "civil_project_assignments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", postgresql.ENUM(
            "CIVIL_MANAGER",
            "TENDERING_OFFICER",
            "CONTRACTS_OFFICER",
            "SUPERVISOR",
            "DELIVERY_COMMISSION",
            "CONTRACTOR",
            "FINANCE_MANAGER",
            name="civil_project_role",
            create_type=False
        ), nullable=False),
        sa.Column("assigned_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "assigned_at IS NOT NULL",
            name="ck_civil_project_assignments_assigned_at_not_null",
        ),
        sa.ForeignKeyConstraint(["project_id"], ["civil_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_civil_project_assignments_id"),
        "civil_project_assignments",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_civil_project_assignments_project_id"),
        "civil_project_assignments",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_civil_project_assignments_role"),
        "civil_project_assignments",
        ["role"],
        unique=False,
    )
    op.create_index(
        op.f("ix_civil_project_assignments_user_id"),
        "civil_project_assignments",
        ["user_id"],
        unique=False,
    )

    op.add_column("users", sa.Column("contractor_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_users_contractor_id"), "users", ["contractor_id"], unique=False)
    op.create_foreign_key(
        "fk_users_contractor_id_contractors",
        "users",
        "contractors",
        ["contractor_id"],
        ["id"],
    )

    op.add_column("credit_requests", sa.Column("civil_project_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_credit_requests_civil_project_id"), "credit_requests", ["civil_project_id"], unique=False)
    op.create_foreign_key(
        "fk_credit_requests_civil_project_id_civil_projects",
        "credit_requests",
        "civil_projects",
        ["civil_project_id"],
        ["id"],
    )

    op.add_column("contracts", sa.Column("civil_project_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_contracts_civil_project_id"), "contracts", ["civil_project_id"], unique=False)
    op.create_foreign_key(
        "fk_contracts_civil_project_id_civil_projects",
        "contracts",
        "civil_projects",
        ["civil_project_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_contracts_civil_project_id_civil_projects", "contracts", type_="foreignkey")
    op.drop_index(op.f("ix_contracts_civil_project_id"), table_name="contracts")
    op.drop_column("contracts", "civil_project_id")

    op.drop_constraint("fk_credit_requests_civil_project_id_civil_projects", "credit_requests", type_="foreignkey")
    op.drop_index(op.f("ix_credit_requests_civil_project_id"), table_name="credit_requests")
    op.drop_column("credit_requests", "civil_project_id")

    op.drop_constraint("fk_users_contractor_id_contractors", "users", type_="foreignkey")
    op.drop_index(op.f("ix_users_contractor_id"), table_name="users")
    op.drop_column("users", "contractor_id")

    op.drop_index(op.f("ix_civil_project_assignments_user_id"), table_name="civil_project_assignments")
    op.drop_index(op.f("ix_civil_project_assignments_role"), table_name="civil_project_assignments")
    op.drop_index(op.f("ix_civil_project_assignments_project_id"), table_name="civil_project_assignments")
    op.drop_index(op.f("ix_civil_project_assignments_id"), table_name="civil_project_assignments")
    op.drop_table("civil_project_assignments")

    op.drop_index(op.f("ix_civil_projects_title"), table_name="civil_projects")
    op.drop_index(op.f("ix_civil_projects_project_code"), table_name="civil_projects")
    op.drop_index(op.f("ix_civil_projects_owning_org_unit_id"), table_name="civil_projects")
    op.drop_index(op.f("ix_civil_projects_id"), table_name="civil_projects")
    op.drop_index(op.f("ix_civil_projects_created_by_id"), table_name="civil_projects")
    op.drop_index(op.f("ix_civil_projects_activity_id"), table_name="civil_projects")
    op.drop_table("civil_projects")

    bind = op.get_bind()
    civil_project_role.drop(bind, checkfirst=True)

"""add financial matrix

Revision ID: b9c8d7e6f5a4
Revises: a8b7c6d5e4f3
Create Date: 2026-05-09 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "b9c8d7e6f5a4"
down_revision: Union[str, None] = "a8b7c6d5e4f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "financial_matrix",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("budget_line_level_5", sa.String(length=64), nullable=False),
        sa.Column("cost_center", sa.String(length=128), nullable=False),
        sa.Column("financial_event", sa.String(length=128), nullable=False),
        sa.Column("activity_name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "budget_line_level_5",
            "cost_center",
            "financial_event",
            "activity_name",
            name="uq_financial_matrix_core_fields",
        ),
    )
    op.create_index(op.f("ix_financial_matrix_id"), "financial_matrix", ["id"], unique=False)
    op.create_index(
        op.f("ix_financial_matrix_budget_line_level_5"),
        "financial_matrix",
        ["budget_line_level_5"],
        unique=False,
    )
    op.create_index(op.f("ix_financial_matrix_cost_center"), "financial_matrix", ["cost_center"], unique=False)
    op.create_index(
        op.f("ix_financial_matrix_financial_event"),
        "financial_matrix",
        ["financial_event"],
        unique=False,
    )
    op.create_index(op.f("ix_financial_matrix_activity_name"), "financial_matrix", ["activity_name"], unique=False)
    op.create_index(op.f("ix_financial_matrix_is_active"), "financial_matrix", ["is_active"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_financial_matrix_is_active"), table_name="financial_matrix")
    op.drop_index(op.f("ix_financial_matrix_activity_name"), table_name="financial_matrix")
    op.drop_index(op.f("ix_financial_matrix_financial_event"), table_name="financial_matrix")
    op.drop_index(op.f("ix_financial_matrix_cost_center"), table_name="financial_matrix")
    op.drop_index(op.f("ix_financial_matrix_budget_line_level_5"), table_name="financial_matrix")
    op.drop_index(op.f("ix_financial_matrix_id"), table_name="financial_matrix")
    op.drop_table("financial_matrix")

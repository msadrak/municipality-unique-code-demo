"""statement event financial matrix

Revision ID: d4e5f6a7b8c9
Revises: c0d1e2f3a4b5
Create Date: 2026-05-11 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c0d1e2f3a4b5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    op.add_column("financial_matrix", sa.Column("project_id", sa.Integer(), nullable=True))
    op.add_column("financial_matrix", sa.Column("statement_document_id", sa.Integer(), nullable=True))
    op.add_column("financial_matrix", sa.Column("transaction_id", sa.Integer(), nullable=True))
    op.add_column("financial_matrix", sa.Column("financial_event_label", sa.String(length=255), nullable=True))
    op.add_column("financial_matrix", sa.Column("event_group", sa.String(length=64), nullable=True))
    op.add_column("financial_matrix", sa.Column("event_sequence", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("financial_matrix", sa.Column("event_direction", sa.String(length=16), nullable=False, server_default="DEBIT"))
    op.add_column("financial_matrix", sa.Column("period_key", sa.String(length=64), nullable=True))
    op.add_column("financial_matrix", sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=True))
    op.add_column("financial_matrix", sa.Column("yekta_code", sa.String(length=128), nullable=True))
    op.add_column(
        "financial_matrix",
        sa.Column("payment_queue_status", sa.String(length=64), nullable=False, server_default="MATRIX_ONLY"),
    )
    op.add_column("financial_matrix", sa.Column("source_payload", sa.JSON(), nullable=True))

    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE financial_matrix DROP CONSTRAINT IF EXISTS uq_financial_matrix_core_fields")
        op.create_foreign_key(
            "fk_financial_matrix_project_id",
            "financial_matrix",
            "civil_projects",
            ["project_id"],
            ["id"],
            ondelete="CASCADE",
        )
        op.create_foreign_key(
            "fk_financial_matrix_statement_document_id",
            "financial_matrix",
            "entity_documents",
            ["statement_document_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_foreign_key(
            "fk_financial_matrix_transaction_id",
            "financial_matrix",
            "transactions",
            ["transaction_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_unique_constraint(
            "uq_financial_matrix_statement_event",
            "financial_matrix",
            ["project_id", "statement_document_id", "financial_event"],
        )

    op.create_index(op.f("ix_financial_matrix_project_id"), "financial_matrix", ["project_id"], unique=False)
    op.create_index(
        op.f("ix_financial_matrix_statement_document_id"),
        "financial_matrix",
        ["statement_document_id"],
        unique=False,
    )
    op.create_index(op.f("ix_financial_matrix_transaction_id"), "financial_matrix", ["transaction_id"], unique=False)
    op.create_index(op.f("ix_financial_matrix_event_group"), "financial_matrix", ["event_group"], unique=False)
    op.create_index(op.f("ix_financial_matrix_period_key"), "financial_matrix", ["period_key"], unique=False)
    op.create_index(op.f("ix_financial_matrix_yekta_code"), "financial_matrix", ["yekta_code"], unique=True)
    op.create_index(
        op.f("ix_financial_matrix_payment_queue_status"),
        "financial_matrix",
        ["payment_queue_status"],
        unique=False,
    )


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_index(op.f("ix_financial_matrix_payment_queue_status"), table_name="financial_matrix")
    op.drop_index(op.f("ix_financial_matrix_yekta_code"), table_name="financial_matrix")
    op.drop_index(op.f("ix_financial_matrix_period_key"), table_name="financial_matrix")
    op.drop_index(op.f("ix_financial_matrix_event_group"), table_name="financial_matrix")
    op.drop_index(op.f("ix_financial_matrix_transaction_id"), table_name="financial_matrix")
    op.drop_index(op.f("ix_financial_matrix_statement_document_id"), table_name="financial_matrix")
    op.drop_index(op.f("ix_financial_matrix_project_id"), table_name="financial_matrix")

    if bind.dialect.name == "postgresql":
        op.drop_constraint("uq_financial_matrix_statement_event", "financial_matrix", type_="unique")
        op.drop_constraint("fk_financial_matrix_transaction_id", "financial_matrix", type_="foreignkey")
        op.drop_constraint("fk_financial_matrix_statement_document_id", "financial_matrix", type_="foreignkey")
        op.drop_constraint("fk_financial_matrix_project_id", "financial_matrix", type_="foreignkey")
        op.create_unique_constraint(
            "uq_financial_matrix_core_fields",
            "financial_matrix",
            ["budget_line_level_5", "cost_center", "financial_event", "activity_name"],
        )

    op.drop_column("financial_matrix", "source_payload")
    op.drop_column("financial_matrix", "payment_queue_status")
    op.drop_column("financial_matrix", "yekta_code")
    op.drop_column("financial_matrix", "amount")
    op.drop_column("financial_matrix", "period_key")
    op.drop_column("financial_matrix", "event_direction")
    op.drop_column("financial_matrix", "event_sequence")
    op.drop_column("financial_matrix", "event_group")
    op.drop_column("financial_matrix", "financial_event_label")
    op.drop_column("financial_matrix", "transaction_id")
    op.drop_column("financial_matrix", "statement_document_id")
    op.drop_column("financial_matrix", "project_id")

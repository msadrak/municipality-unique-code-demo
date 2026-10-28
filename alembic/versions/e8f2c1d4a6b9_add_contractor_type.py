"""add contractor type

Revision ID: e8f2c1d4a6b9
Revises: d4e5f6a7b8c9
Create Date: 2026-05-31 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "e8f2c1d4a6b9"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    existing_columns = {column["name"] for column in inspect(bind).get_columns("contractors")}
    if "contractor_type" not in existing_columns:
        op.add_column(
            "contractors",
            sa.Column("contractor_type", sa.String(), nullable=False, server_default="CORPORATE"),
        )
    op.execute(
        "UPDATE contractors SET contractor_type = 'CORPORATE' "
        "WHERE contractor_type IS NULL OR contractor_type = ''"
    )


def downgrade() -> None:
    bind = op.get_bind()
    existing_columns = {column["name"] for column in inspect(bind).get_columns("contractors")}
    if "contractor_type" in existing_columns:
        op.drop_column("contractors", "contractor_type")

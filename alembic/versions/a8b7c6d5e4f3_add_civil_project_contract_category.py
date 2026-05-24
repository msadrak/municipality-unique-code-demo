"""add civil project contract category

Revision ID: a8b7c6d5e4f3
Revises: 55c9d5c1d0b7
Create Date: 2026-05-09 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "a8b7c6d5e4f3"
down_revision: Union[str, None] = "55c9d5c1d0b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE civil_projects
        ADD COLUMN IF NOT EXISTS contract_category VARCHAR(128) NULL
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_civil_projects_contract_category
        ON civil_projects(contract_category)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_civil_projects_contract_category")
    op.execute("ALTER TABLE civil_projects DROP COLUMN IF EXISTS contract_category")

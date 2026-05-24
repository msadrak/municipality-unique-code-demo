"""add yekta code to civil projects

Revision ID: c0d1e2f3a4b5
Revises: b9c8d7e6f5a4
Create Date: 2026-05-09 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "c0d1e2f3a4b5"
down_revision: Union[str, None] = "b9c8d7e6f5a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE civil_projects
        ADD COLUMN IF NOT EXISTS yekta_code VARCHAR(128) NULL
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ix_civil_projects_yekta_code
        ON civil_projects(yekta_code)
        WHERE yekta_code IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_civil_projects_yekta_code")
    op.execute("ALTER TABLE civil_projects DROP COLUMN IF EXISTS yekta_code")

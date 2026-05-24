"""add civil project contractor user link

Revision ID: 55c9d5c1d0b7
Revises: b7c4d9e2f103
Create Date: 2026-05-02 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "55c9d5c1d0b7"
down_revision: Union[str, None] = "b7c4d9e2f103"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE civil_projects
        ADD COLUMN IF NOT EXISTS contractor_id INTEGER NULL
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_civil_projects_contractor_id
        ON civil_projects(contractor_id)
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'fk_civil_projects_contractor_id_users'
            ) THEN
                ALTER TABLE civil_projects
                ADD CONSTRAINT fk_civil_projects_contractor_id_users
                FOREIGN KEY (contractor_id)
                REFERENCES users(id)
                ON DELETE SET NULL;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE civil_projects DROP CONSTRAINT IF EXISTS fk_civil_projects_contractor_id_users")
    op.execute("DROP INDEX IF EXISTS ix_civil_projects_contractor_id")
    op.execute("ALTER TABLE civil_projects DROP COLUMN IF EXISTS contractor_id")

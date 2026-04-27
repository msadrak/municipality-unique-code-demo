"""add_pending_unique_code_to_workflow_status

Revision ID: f4d3c7a9b21e
Revises: c23c0985593a
Create Date: 2026-04-19 11:40:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "f4d3c7a9b21e"
down_revision: Union[str, None] = "c23c0985593a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE work_flow_status ADD VALUE IF NOT EXISTS 'PENDING_UNIQUE_CODE'")


def downgrade() -> None:
    # PostgreSQL enum values cannot be removed safely without rebuilding the type.
    pass

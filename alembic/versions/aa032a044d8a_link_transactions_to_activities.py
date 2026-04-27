"""link_transactions_to_activities

Revision ID: aa032a044d8a
Revises: 46feab428012
Create Date: 2026-04-21 09:43:39.374568

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aa032a044d8a'
down_revision: Union[str, None] = '46feab428012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "transactions",
        sa.Column("activity_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        op.f("ix_transactions_activity_id"),
        "transactions",
        ["activity_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_transactions_activity_id_activities",
        "transactions",
        "activities",
        ["activity_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_transactions_activity_id_activities",
        "transactions",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_transactions_activity_id"), table_name="transactions")
    op.drop_column("transactions", "activity_id")

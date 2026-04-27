"""add transaction allocations

Revision ID: 52c174e4cdc7
Revises: aa032a044d8a
Create Date: 2026-04-21 11:29:58.671781

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '52c174e4cdc7'
down_revision: Union[str, None] = 'aa032a044d8a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'transaction_allocations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('transaction_id', sa.Integer(), nullable=False),
        sa.Column('org_unit_name', sa.String(length=255), nullable=False),
        sa.Column('cost_center_code', sa.String(length=64), nullable=False),
        sa.Column('budget_line_code', sa.String(length=64), nullable=False),
        sa.Column('allocated_amount', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('legal_deductions', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('penalties', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('net_amount', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('unique_code', sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(['transaction_id'], ['transactions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_transaction_allocations_budget_line_code'), 'transaction_allocations', ['budget_line_code'], unique=False)
    op.create_index(op.f('ix_transaction_allocations_cost_center_code'), 'transaction_allocations', ['cost_center_code'], unique=False)
    op.create_index(op.f('ix_transaction_allocations_id'), 'transaction_allocations', ['id'], unique=False)
    op.create_index(op.f('ix_transaction_allocations_transaction_id'), 'transaction_allocations', ['transaction_id'], unique=False)
    op.create_index(op.f('ix_transaction_allocations_unique_code'), 'transaction_allocations', ['unique_code'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_transaction_allocations_unique_code'), table_name='transaction_allocations')
    op.drop_index(op.f('ix_transaction_allocations_transaction_id'), table_name='transaction_allocations')
    op.drop_index(op.f('ix_transaction_allocations_id'), table_name='transaction_allocations')
    op.drop_index(op.f('ix_transaction_allocations_cost_center_code'), table_name='transaction_allocations')
    op.drop_index(op.f('ix_transaction_allocations_budget_line_code'), table_name='transaction_allocations')
    op.drop_table('transaction_allocations')

"""add provisioning_status, job_id to order_items and dispatch_logs table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-26 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add provisioning columns to order_items
    op.add_column('order_items', sa.Column('provisioning_status', sa.String(20), nullable=False, server_default='not_started'))
    op.add_column('order_items', sa.Column('job_id', sa.String(100), nullable=True))

    # Create dispatch_logs table
    op.create_table(
        'dispatch_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('order_id', sa.String(36), nullable=False),
        sa.Column('order_item_id', sa.String(36), nullable=False),
        sa.Column('job_id', sa.String(100), nullable=True),
        sa.Column('dispatch_method', sa.String(20), nullable=False),
        sa.Column('dispatched_at', sa.DateTime(timezone=True)),
        sa.Column('attempt_count', sa.Integer, nullable=False, server_default='1'),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('error_message', sa.Text, nullable=True),
    )
    op.create_index('ix_dispatch_logs_order_id', 'dispatch_logs', ['order_id'])
    op.create_index('ix_dispatch_logs_order_item_id', 'dispatch_logs', ['order_item_id'])


def downgrade() -> None:
    op.drop_index('ix_dispatch_logs_order_item_id', 'dispatch_logs')
    op.drop_index('ix_dispatch_logs_order_id', 'dispatch_logs')
    op.drop_table('dispatch_logs')
    op.drop_column('order_items', 'job_id')
    op.drop_column('order_items', 'provisioning_status')

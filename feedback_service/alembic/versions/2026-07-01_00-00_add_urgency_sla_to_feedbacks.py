"""Add is_urgent and sla_deadline to feedbacks

Revision ID: b3c4d5e6f7a8
Revises: h5i6j7k8l9m0
Create Date: 2026-07-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "b3c4d5e6f7a8"
down_revision = "h5i6j7k8l9m0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('feedbacks', sa.Column('is_urgent', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('feedbacks', sa.Column('sla_deadline', sa.DateTime(timezone=True), nullable=True))
    op.create_index('ix_feedbacks_is_urgent', 'feedbacks', ['is_urgent'])
    op.create_index('ix_feedbacks_sla_deadline', 'feedbacks', ['sla_deadline'])


def downgrade() -> None:
    op.drop_index('ix_feedbacks_sla_deadline', table_name='feedbacks')
    op.drop_index('ix_feedbacks_is_urgent', table_name='feedbacks')
    op.drop_column('feedbacks', 'sla_deadline')
    op.drop_column('feedbacks', 'is_urgent')

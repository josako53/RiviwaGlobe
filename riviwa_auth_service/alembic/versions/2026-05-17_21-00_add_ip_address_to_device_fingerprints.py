"""add ip_address to device_fingerprints

Revision ID: c7d8e9f0a1b2
Revises: a1b2c3d4e5f6
Create Date: 2026-05-17 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'c7d8e9f0a1b2'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'device_fingerprints',
        sa.Column('ip_address', sa.String(45), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('device_fingerprints', 'ip_address')

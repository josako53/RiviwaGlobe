"""add ip_address to device_fingerprints

Revision ID: a1b2c3d4e5f6
Revises: 2026-05-05
Create Date: 2026-05-17 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = None   # set by alembic at runtime via branch resolution
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'device_fingerprints',
        sa.Column('ip_address', sa.String(45), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('device_fingerprints', 'ip_address')

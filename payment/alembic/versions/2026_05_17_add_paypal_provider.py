"""Add paypal to payment provider enums.

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-05-17
"""
from alembic import op

revision = 'a1b2c3d4e5f6'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add 'paypal' to all provider enums (IF NOT EXISTS — safe to run multiple times)
    op.execute("ALTER TYPE transaction_provider ADD VALUE IF NOT EXISTS 'paypal'")
    op.execute("ALTER TYPE webhook_provider ADD VALUE IF NOT EXISTS 'paypal'")


def downgrade() -> None:
    # Postgres does not support removing enum values — downgrade is a no-op
    pass

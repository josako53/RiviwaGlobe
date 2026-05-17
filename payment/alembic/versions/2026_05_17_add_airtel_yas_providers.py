"""Add airtel and yas to payment provider enums.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-17
"""
from alembic import op

revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE transaction_provider ADD VALUE IF NOT EXISTS 'airtel'")
    op.execute("ALTER TYPE transaction_provider ADD VALUE IF NOT EXISTS 'yas'")
    op.execute("ALTER TYPE webhook_provider    ADD VALUE IF NOT EXISTS 'airtel'")
    op.execute("ALTER TYPE webhook_provider    ADD VALUE IF NOT EXISTS 'yas'")


def downgrade() -> None:
    pass   # Postgres does not support removing enum values

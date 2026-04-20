"""add_inquiry_feedback_type

Revision ID: b3c4d5e6f7a8
Revises: a1b2c3d4e5f6
Create Date: 2026-04-20 13:00:00.000000+00:00

Adds INQUIRY as a new FeedbackType enum value and adds inquiry-specific
FeedbackCategory values. PostgreSQL enum ADD VALUE must run outside a
transaction block (autocommit required).
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "b3c4d5e6f7a8"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    connection.execution_options(isolation_level="AUTOCOMMIT")

    connection.execute(sa.text("ALTER TYPE feedback_type ADD VALUE IF NOT EXISTS 'inquiry'"))

    for val in ("information_request", "procedure_inquiry", "status_update",
                "document_request", "general_inquiry"):
        connection.execute(sa.text(f"ALTER TYPE feedback_category ADD VALUE IF NOT EXISTS '{val}'"))

    connection.execution_options(isolation_level="READ_COMMITTED")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values without recreating the type.
    # Downgrade is a no-op — the values remain harmless if unused.
    pass

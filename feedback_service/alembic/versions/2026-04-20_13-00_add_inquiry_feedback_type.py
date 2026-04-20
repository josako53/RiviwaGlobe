"""add_inquiry_feedback_type

Revision ID: a5b6c7d8e9f0
Revises: f4a5b6c7d8e9
Create Date: 2026-04-20 13:00:00.000000+00:00

Adds INQUIRY as a new FeedbackType enum value and adds inquiry-specific
FeedbackCategory values. PostgreSQL 12+ allows ADD VALUE inside a transaction.
Enum labels are uppercase to match the existing convention (GRIEVANCE, SUGGESTION, APPLAUSE).
"""
from __future__ import annotations

from alembic import op

revision = "a5b6c7d8e9f0"
down_revision = "f4a5b6c7d8e9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE feedback_type ADD VALUE IF NOT EXISTS 'INQUIRY'")

    for val in ("INFORMATION_REQUEST", "PROCEDURE_INQUIRY", "STATUS_UPDATE",
                "DOCUMENT_REQUEST", "GENERAL_INQUIRY"):
        op.execute(f"ALTER TYPE feedback_category ADD VALUE IF NOT EXISTS '{val}'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values without recreating the type.
    # Downgrade is a no-op — the values remain harmless if unused.
    pass

"""add_department_id_to_feedbacks

Revision ID: f3a4b5c6d7e8
Revises: e5f6a7b8c9d0
Create Date: 2026-04-20 10:00:00.000000+00:00

Adds a soft-FK column to feedbacks so a submission can be tagged to a
specific department (HR, Finance, Customer Care, etc.) from the auth service.

This is intentionally a plain UUID column with no DB-level FK constraint
because feedbacks live in feedback_db while departments live in auth_db.
The auth service resolves the UUID to a department name when needed.

Changes
────────
  · feedbacks.department_id  UUID  nullable  indexed  (new)
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision      = "f3a4b5c6d7e8"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.add_column(
        "feedbacks",
        sa.Column("department_id", sa.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_feedbacks_department_id", "feedbacks", ["department_id"])


def downgrade() -> None:
    op.drop_index("ix_feedbacks_department_id", table_name="feedbacks")
    op.drop_column("feedbacks", "department_id")

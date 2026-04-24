"""add_branch_id_to_feedbacks

Revision ID: c7d8e9f0a1b2
Revises: b6c7d8e9f0a1
Create Date: 2026-04-24 10:00:00.000000+00:00

Adds branch_id to feedbacks so analytics can group/compare by org branch.
Intentionally a plain UUID with no DB-level FK — org_branches lives in auth_db.
Populated at submission time when department_id is provided, via internal
auth service call (GET /internal/departments/{dept_id}).

Changes
────────
  · feedbacks.branch_id  UUID  nullable  indexed  (new)
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision      = "c7d8e9f0a1b2"
down_revision = "b6c7d8e9f0a1"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.add_column(
        "feedbacks",
        sa.Column("branch_id", sa.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_feedbacks_branch_id", "feedbacks", ["branch_id"])


def downgrade() -> None:
    op.drop_index("ix_feedbacks_branch_id", table_name="feedbacks")
    op.drop_column("feedbacks", "branch_id")

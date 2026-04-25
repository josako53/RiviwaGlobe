"""make_feedback_project_id_nullable

Revision ID: d8e9f0a1b2c3
Revises: c7d8e9f0a1b2
Create Date: 2026-04-25 12:00:00.000000+00:00

Allows feedback.project_id to be NULL so consumers can submit
org-level feedback (about a company, service, or branch) without
requiring a specific project context.

Changes
────────
  · feedbacks.project_id  — drop NOT NULL, change ON DELETE CASCADE
    to ON DELETE SET NULL
"""
from __future__ import annotations
import sqlalchemy as sa
from alembic import op


revision      = "d8e9f0a1b2c3"
down_revision = "c7d8e9f0a1b2"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    # Drop the existing FK constraint (CASCADE)
    op.drop_constraint("feedbacks_project_id_fkey", "feedbacks", type_="foreignkey")
    # Make the column nullable
    op.alter_column("feedbacks", "project_id", nullable=True)
    # Re-add FK with SET NULL on delete
    op.create_foreign_key(
        "feedbacks_project_id_fkey",
        "feedbacks", "fb_projects",
        ["project_id"], ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("feedbacks_project_id_fkey", "feedbacks", type_="foreignkey")
    op.alter_column("feedbacks", "project_id", nullable=False)
    op.create_foreign_key(
        "feedbacks_project_id_fkey",
        "feedbacks", "fb_projects",
        ["project_id"], ["id"],
        ondelete="CASCADE",
    )

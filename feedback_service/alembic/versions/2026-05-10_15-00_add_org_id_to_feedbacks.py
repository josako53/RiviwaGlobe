"""Add org_id to feedbacks — enables org-scoped feedback without a project.

Revision ID: e9f0a1b2c3d4
Revises: d8e9f0a1b2c3
Create Date: 2026-05-10 15:00:00

WHY
───
Previously, org context on feedback was only accessible via a JOIN
through fb_projects (p.organisation_id). This meant:
  1. Every feedback submission required a project to exist first.
  2. Org-level analytics had mandatory JOIN overhead on every query.
  3. Feedback about a branch, department, or service — without a GRM
     project — was architecturally impossible.

This migration adds org_id directly on feedbacks (denormalised at
submission time), decoupling org analytics from the projects table.
"""
from alembic import op
import sqlalchemy as sa

revision      = "e9f0a1b2c3d4"
down_revision = "d8e9f0a1b2c3"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.add_column(
        "feedbacks",
        sa.Column("org_id", sa.UUID(), nullable=True),
    )
    op.create_index("ix_feedbacks_org_id", "feedbacks", ["org_id"])

    # Back-fill org_id for existing feedback that has a project
    op.execute("""
        UPDATE feedbacks f
        SET    org_id = p.organisation_id
        FROM   fb_projects p
        WHERE  f.project_id = p.id
          AND  f.org_id IS NULL
    """)


def downgrade() -> None:
    op.drop_index("ix_feedbacks_org_id", table_name="feedbacks")
    op.drop_column("feedbacks", "org_id")

"""Make feedback.category nullable; add DB-level defaults for priority and current_level

Revision ID: 7d8e9f0a1b2c
Revises: 6c7d8e9f0a1b
Create Date: 2026-06-24 16:00:00.000000+00:00

category is a legacy enum field superseded by category_def_id (dynamic categories).
Making it nullable means submissions that don't specify a legacy category are still
stored without error — category_def_id carries the authoritative value.

priority and current_level already have Python-level defaults (MEDIUM / WARD) in the
ORM model but had no DB-level DEFAULT clause, so raw SQL inserts failed.  Adding
server-side defaults makes the columns self-consistent at every insertion path.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "7d8e9f0a1b2c"
down_revision = "6c7d8e9f0a1b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Make the legacy category enum nullable
    op.alter_column(
        "feedbacks",
        "category",
        existing_type=sa.Enum(
            "COMMUNICATION", "SAFETY", "ENVIRONMENTAL", "ACCESSIBILITY", "OTHER",
            "COMPENSATION", "RESETTLEMENT", "LAND_ACQUISITION", "CONSTRUCTION_IMPACT",
            "TRAFFIC", "WORKER_RIGHTS", "SAFETY_HAZARD", "ENGAGEMENT", "DESIGN_ISSUE",
            "PROJECT_DELAY", "CORRUPTION", "DESIGN", "PROCESS", "COMMUNITY_BENEFIT",
            "EMPLOYMENT", "QUALITY", "TIMELINESS", "STAFF_CONDUCT", "COMMUNITY_IMPACT",
            "RESPONSIVENESS", "INFORMATION_REQUEST", "PROCEDURE_INQUIRY", "STATUS_UPDATE",
            "DOCUMENT_REQUEST", "GENERAL_INQUIRY",
            name="feedback_category",
        ),
        nullable=True,
        existing_nullable=False,
    )

    # Add DB-level defaults so raw inserts never fail on these required fields
    op.execute("ALTER TABLE feedbacks ALTER COLUMN priority SET DEFAULT 'MEDIUM'")
    op.execute("ALTER TABLE feedbacks ALTER COLUMN current_level SET DEFAULT 'WARD'")


def downgrade() -> None:
    op.execute("ALTER TABLE feedbacks ALTER COLUMN priority DROP DEFAULT")
    op.execute("ALTER TABLE feedbacks ALTER COLUMN current_level DROP DEFAULT")
    op.alter_column(
        "feedbacks",
        "category",
        existing_type=sa.Enum(name="feedback_category"),
        nullable=False,
        existing_nullable=True,
    )

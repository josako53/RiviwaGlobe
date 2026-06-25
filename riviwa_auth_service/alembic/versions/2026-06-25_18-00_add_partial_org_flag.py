"""Add is_partial and partial_meta to organisations

Revision ID: c1d2e3f4a5b6
Revises: f7a8b9c0d1e2
Create Date: 2026-06-25 18:00:00.000000+00:00

Supports Matter 3: when a Riviwa AI conversation references an organisation
that is not yet registered on the platform, a partial/placeholder Organisation
row is created automatically so feedback can still be submitted and tracked.

is_partial  — boolean flag (default False); True for AI-created placeholders.
partial_meta — JSONB with AI context: suggested_name, sector, city, source,
               submitter_user_id, feedback_count.

Partial orgs are visible only to Riviwa platform admins, who can then contact
the real organisation and convert the placeholder to a full account.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "c1d2e3f4a5b6"
down_revision = "f3a4b5c6d7e8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "organisations",
        sa.Column("is_partial", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "organisations",
        sa.Column("partial_meta", JSONB(), nullable=True),
    )
    op.create_index("ix_organisations_is_partial", "organisations", ["is_partial"])


def downgrade() -> None:
    op.drop_index("ix_organisations_is_partial", table_name="organisations")
    op.drop_column("organisations", "partial_meta")
    op.drop_column("organisations", "is_partial")

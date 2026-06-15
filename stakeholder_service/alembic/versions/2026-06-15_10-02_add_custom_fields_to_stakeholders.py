"""add_custom_fields_to_stakeholders

Revision ID: b7e9f2a1c4d8
Revises: a1b2c3d4e5f6
Create Date: 2026-06-15 10:02:00.000000+00:00

Adds a JSONB custom_fields column to the stakeholders table so that
organisations can store arbitrary project-specific attributes (e.g.
beneficiary_id, vulnerability_score) without requiring schema changes.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "b7e9f2a1c4d8"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "stakeholders",
        sa.Column("custom_fields", JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("stakeholders", "custom_fields")

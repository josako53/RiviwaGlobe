"""add_org_display_name_to_fb_projects

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-04-20 14:00:00.000000+00:00

Adds org_display_name to fb_projects so analytics/AI can resolve org
names without cross-service HTTP calls at query time.  Populated by
org.created and org.updated Kafka events.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "c4d5e6f7a8b9"
down_revision = "b3c4d5e6f7a8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "fb_projects",
        sa.Column("org_display_name", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("fb_projects", "org_display_name")

"""add_system_settings

Revision ID: d4e5f6a7b8c9
Revises: 9df162bad3f3
Create Date: 2026-04-12 01:00:00.000000+00:00

Creates the system_settings table (single-row platform config) and seeds
the default row so the app always has settings to read on first boot.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from datetime import datetime, timezone

revision    = "d4e5f6a7b8c9"
down_revision = "9df162bad3f3"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.create_table(
        "system_settings",
        sa.Column("id",              sa.Integer,     primary_key=True),
        sa.Column("app_name",        sa.String(128), nullable=False, server_default="Riviwa GRM"),
        sa.Column("logo_url",        sa.String(512), nullable=True),
        sa.Column("logo_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("logo_updated_by", sa.Uuid,        nullable=True),
        sa.Column("favicon_url",     sa.String(512), nullable=True),
        sa.Column("support_email",   sa.String(255), nullable=True, server_default="support@riviwa.com"),
        sa.Column("support_phone",   sa.String(30),  nullable=True),
        sa.Column("primary_color",   sa.String(7),   nullable=False, server_default="#185FA5"),
        sa.Column("secondary_color", sa.String(7),   nullable=False, server_default="#1D9E75"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    # Seed the single default row
    op.execute("""
        INSERT INTO system_settings
            (id, app_name, support_email, primary_color, secondary_color, updated_at)
        VALUES
            (1, 'Riviwa GRM', 'support@riviwa.com', '#185FA5', '#1D9E75', NOW())
        ON CONFLICT (id) DO NOTHING
    """)


def downgrade() -> None:
    op.drop_table("system_settings")

"""Add org_id and org_display_name to channel_sessions

Revision ID: h5i6j7k8l9m0
Revises: g4h5i6j7k8l9
Create Date: 2026-06-25 18:00:00.000000+00:00

Supports org-aware AI sessions (Matter 1-3):

org_id           — auth_service Organisation.id resolved from any of five
                   entry points: GPS coordinates, QR code scan, SMS org-code,
                   user selecting an org page on Riviwa, or CMS post context.
                   Also set during conversation when AI resolves the org from
                   what the user describes (Matter 2), or when a partial org
                   is created for an unregistered organisation (Matter 3).

org_display_name — cached org display name so the greeting and context
                   messages don't require a repeated auth_service lookup.
                   Populated at session creation or when org is resolved.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "h5i6j7k8l9m0"
down_revision = "g4h5i6j7k8l9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("channel_sessions", sa.Column("org_id", sa.UUID(), nullable=True))
    op.add_column("channel_sessions", sa.Column("org_display_name", sa.String(255), nullable=True))
    op.create_index("ix_channel_sessions_org_id", "channel_sessions", ["org_id"])


def downgrade() -> None:
    op.drop_index("ix_channel_sessions_org_id", table_name="channel_sessions")
    op.drop_column("channel_sessions", "org_display_name")
    op.drop_column("channel_sessions", "org_id")

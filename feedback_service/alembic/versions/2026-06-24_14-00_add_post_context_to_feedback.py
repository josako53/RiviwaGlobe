"""Add post_id and post_slug to feedbacks and channel_sessions

Revision ID: 6c7d8e9f0a1b
Revises: bf1c2d3e4f5a
Create Date: 2026-06-24 14:00:00.000000+00:00

Links feedback submissions and channel sessions to the CMS post that
triggered them, enabling per-post engagement analytics.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "6c7d8e9f0a1b"
down_revision: Union[str, None] = "bf1c2d3e4f5a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on:    Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("feedbacks",       sa.Column("post_id",   sa.UUID(),          nullable=True))
    op.add_column("feedbacks",       sa.Column("post_slug", sa.String(500),      nullable=True))
    op.add_column("channel_sessions", sa.Column("post_id",   sa.UUID(),          nullable=True))
    op.add_column("channel_sessions", sa.Column("post_slug", sa.String(500),      nullable=True))

    op.create_index("ix_feedbacks_post_id",        "feedbacks",        ["post_id"])
    op.create_index("ix_channel_sessions_post_id", "channel_sessions", ["post_id"])


def downgrade() -> None:
    op.drop_index("ix_channel_sessions_post_id", table_name="channel_sessions")
    op.drop_index("ix_feedbacks_post_id",        table_name="feedbacks")

    op.drop_column("channel_sessions", "post_slug")
    op.drop_column("channel_sessions", "post_id")
    op.drop_column("feedbacks",        "post_slug")
    op.drop_column("feedbacks",        "post_id")

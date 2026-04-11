"""add_missing_channel_session_columns

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-11 10:30:00.000000+00:00

Safely adds newer columns to channel_sessions that may be missing from older deployments.
Uses IF NOT EXISTS so this is safe to run even if columns already exist.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add newer columns to channel_sessions that may be missing from older deployments.
    # Using raw PostgreSQL IF NOT EXISTS for safety.
    op.execute("""
        ALTER TABLE channel_sessions
            ADD COLUMN IF NOT EXISTS contact_id          UUID,
            ADD COLUMN IF NOT EXISTS is_officer_assisted BOOLEAN NOT NULL DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS recorded_by_user_id UUID,
            ADD COLUMN IF NOT EXISTS is_voice_session    BOOLEAN NOT NULL DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS audio_recording_url TEXT,
            ADD COLUMN IF NOT EXISTS audio_duration_seconds INTEGER,
            ADD COLUMN IF NOT EXISTS transcription       TEXT,
            ADD COLUMN IF NOT EXISTS transcription_service VARCHAR(50),
            ADD COLUMN IF NOT EXISTS transcription_confidence DOUBLE PRECISION;
    """)


def downgrade() -> None:
    pass

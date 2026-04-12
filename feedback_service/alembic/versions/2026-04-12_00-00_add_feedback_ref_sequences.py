"""add_feedback_ref_sequences

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-04-12 00:00:00.000000+00:00

Replaces the MAX()-based unique_ref generation with an atomic counter table.
The table holds one row per (prefix, year). Each call atomically increments
last_value and returns the new number — no race conditions at any scale.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "feedback_ref_sequences",
        sa.Column("prefix", sa.String(10), nullable=False),
        sa.Column("year",   sa.Integer,    nullable=False),
        sa.Column("last_value", sa.Integer, nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("prefix", "year", name="pk_feedback_ref_sequences"),
    )

    # Seed from existing data so the counter starts after the highest ref already in the DB.
    # E.g. if GRV-2026-0009 already exists, seed last_value=9 so next call returns 10.
    op.execute("""
        INSERT INTO feedback_ref_sequences (prefix, year, last_value)
        SELECT
            SPLIT_PART(unique_ref, '-', 1)                   AS prefix,
            CAST(SPLIT_PART(unique_ref, '-', 2) AS INTEGER)  AS year,
            MAX(CAST(SPLIT_PART(unique_ref, '-', 3) AS INTEGER)) AS last_value
        FROM feedbacks
        WHERE unique_ref ~ '^[A-Z]+-[0-9]{4}-[0-9]+$'
        GROUP BY prefix, year
        ON CONFLICT (prefix, year) DO UPDATE
            SET last_value = EXCLUDED.last_value
    """)


def downgrade() -> None:
    op.drop_table("feedback_ref_sequences")

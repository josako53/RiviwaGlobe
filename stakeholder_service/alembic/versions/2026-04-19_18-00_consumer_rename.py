"""consumer_rename

Revision ID: a1b2c3d4e5f6
Revises: None
Create Date: 2026-04-19 18:00:00.000000+00:00

Renames the "pap" terminology to "consumer" in the stakeholder_db:

  1. stakeholder_type enum:   "pap"    → "consumer"
  2. stakeholder_projects:    is_pap   → is_consumer   (column rename)

Rationale:
  Riviwa is not limited to infrastructure projects. Any person affected by
  an organisation's services, branch, product, or operation is a Consumer.
  "Project Affected Person" is too narrow for the platform's scope.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "a1b2c3d4e5f6"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Rename enum value "pap" → "consumer" ───────────────────────────────
    # PostgreSQL supports ALTER TYPE … RENAME VALUE since v10.
    # This is safe to run on an existing DB — existing rows keep their value
    # automatically updated by the engine.
    op.execute("ALTER TYPE stakeholder_type RENAME VALUE 'pap' TO 'consumer'")

    # ── 2. Rename column is_pap → is_consumer on stakeholder_projects ─────────
    op.alter_column(
        "stakeholder_projects",
        "is_pap",
        new_column_name="is_consumer",
        existing_type=sa.Boolean(),
        existing_nullable=False,
    )


def downgrade() -> None:
    # Reverse column rename
    op.alter_column(
        "stakeholder_projects",
        "is_consumer",
        new_column_name="is_pap",
        existing_type=sa.Boolean(),
        existing_nullable=False,
    )

    # Reverse enum value rename
    op.execute("ALTER TYPE stakeholder_type RENAME VALUE 'consumer' TO 'pap'")

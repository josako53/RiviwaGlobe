"""consumer_rename

Revision ID: a1b2c3d4e5f6
Revises: None
Create Date: 2026-04-19 18:00:00.000000+00:00

Renames terminology in the stakeholder_db:

  1. stakeholder_type enum:       "pap"  → "consumer"
  2. stakeholder_projects:        is_pap → is_consumer   (column rename)
  3. focal_person_org_type enum:  "piu"  → "grm_unit"

Rationale:
  Riviwa is not limited to infrastructure projects. Any person affected by
  an organisation's services, branch, product, or operation is a Consumer.
  "Project Affected Person" is too narrow for the platform's scope.
  Similarly, "PIU" (Project Implementing Unit) is replaced with "GRM Unit"
  to reflect that any team — branch, department, or organisation — can handle
  grievances without being tied to a specific project implementation unit.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "a1b2c3d4e5f6"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Rename enum value "PAP" → "consumer" (idempotent) ─────────────────
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_enum e JOIN pg_type t ON e.enumtypid = t.oid
                WHERE t.typname = 'stakeholder_type' AND e.enumlabel = 'PAP'
            ) THEN
                ALTER TYPE stakeholder_type RENAME VALUE 'PAP' TO 'consumer';
            END IF;
        END $$;
    """)

    # ── 2. Rename column is_pap → is_consumer on stakeholder_projects ────────
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'stakeholder_projects' AND column_name = 'is_pap'
            ) THEN
                ALTER TABLE stakeholder_projects RENAME COLUMN is_pap TO is_consumer;
            END IF;
        END $$;
    """)

    # ── 3. Rename focal_person_org_type enum value "PIU" → "grm_unit" ────────
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_enum e JOIN pg_type t ON e.enumtypid = t.oid
                WHERE t.typname = 'focal_person_org_type' AND e.enumlabel = 'PIU'
            ) THEN
                ALTER TYPE focal_person_org_type RENAME VALUE 'PIU' TO 'grm_unit';
            END IF;
        END $$;
    """)


def downgrade() -> None:
    # Reverse focal_person_org_type rename
    op.execute("ALTER TYPE focal_person_org_type RENAME VALUE 'grm_unit' TO 'PIU'")

    # Reverse column rename
    op.alter_column(
        "stakeholder_projects",
        "is_consumer",
        new_column_name="is_pap",
        existing_type=sa.Boolean(),
        existing_nullable=False,
    )

    # Reverse enum value rename
    op.execute("ALTER TYPE stakeholder_type RENAME VALUE 'consumer' TO 'PAP'")

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
    # ── 1. Rename enum value "PAP" → "consumer" ───────────────────────────────
    # PostgreSQL supports ALTER TYPE … RENAME VALUE since v10.
    # DB stores uppercase labels (PAP, INTERESTED_PARTY, etc.)
    op.execute("ALTER TYPE stakeholder_type RENAME VALUE 'PAP' TO 'consumer'")

    # ── 2. Rename column is_pap → is_consumer on stakeholder_projects ─────────
    op.alter_column(
        "stakeholder_projects",
        "is_pap",
        new_column_name="is_consumer",
        existing_type=sa.Boolean(),
        existing_nullable=False,
    )

    # ── 3. Rename focal_person_org_type enum value "PIU" → "grm_unit" ─────────
    op.execute("ALTER TYPE focal_person_org_type RENAME VALUE 'PIU' TO 'grm_unit'")


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

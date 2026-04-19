"""rename_grm_enum_values

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-04-19 20:00:00.000000+00:00

Renames GRM-related enum values in feedback_db to remove project-centric
terminology and replace with generic equivalents:

  grm_level enum:
    "lga_piu"  → "lga_grm_unit"      (LGA Project Implementing Unit → LGA GRM Unit)
    "pcu"      → "coordinating_unit"  (Project Coordinating Unit → Coordinating Unit)

  committee_level enum:
    "lga_piu"  → "lga_grm_unit"
    "pcu"      → "coordinating_unit"

Rationale:
  Riviwa is not limited to infrastructure projects. The "PIU" and "PCU" labels
  are specific to World Bank project structures. Any organisation (businesses,
  NGOs, financial institutions, etc.) can use the GRM — their teams are
  generically "GRM Units" and "Coordinating Units".

PostgreSQL supports ALTER TYPE … RENAME VALUE since v10 — safe for live DBs.
"""
from __future__ import annotations

from alembic import op


revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── grm_level enum ────────────────────────────────────────────────────────
    op.execute("ALTER TYPE grm_level RENAME VALUE 'lga_piu' TO 'lga_grm_unit'")
    op.execute("ALTER TYPE grm_level RENAME VALUE 'pcu' TO 'coordinating_unit'")

    # ── committee_level enum ──────────────────────────────────────────────────
    op.execute("ALTER TYPE committee_level RENAME VALUE 'lga_piu' TO 'lga_grm_unit'")
    op.execute("ALTER TYPE committee_level RENAME VALUE 'pcu' TO 'coordinating_unit'")


def downgrade() -> None:
    # ── committee_level enum ──────────────────────────────────────────────────
    op.execute("ALTER TYPE committee_level RENAME VALUE 'coordinating_unit' TO 'pcu'")
    op.execute("ALTER TYPE committee_level RENAME VALUE 'lga_grm_unit' TO 'lga_piu'")

    # ── grm_level enum ────────────────────────────────────────────────────────
    op.execute("ALTER TYPE grm_level RENAME VALUE 'coordinating_unit' TO 'pcu'")
    op.execute("ALTER TYPE grm_level RENAME VALUE 'lga_grm_unit' TO 'lga_piu'")

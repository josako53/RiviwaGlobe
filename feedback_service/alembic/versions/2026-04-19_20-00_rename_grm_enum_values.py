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

  grm_from_level enum (FeedbackEscalation.from_level):
    "lga_piu"  → "lga_grm_unit"
    "pcu"      → "coordinating_unit"

  grm_to_level enum (FeedbackEscalation.to_level):
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
    # ── grm_level enum (Feedback.current_level) ──────────────────────────────
    op.execute("ALTER TYPE grm_level RENAME VALUE 'LGA_PIU' TO 'lga_grm_unit'")
    op.execute("ALTER TYPE grm_level RENAME VALUE 'PCU' TO 'coordinating_unit'")

    # ── committee_level enum ──────────────────────────────────────────────────
    op.execute("ALTER TYPE committee_level RENAME VALUE 'LGA_PIU' TO 'lga_grm_unit'")
    op.execute("ALTER TYPE committee_level RENAME VALUE 'PCU' TO 'coordinating_unit'")

    # ── grm_from_level enum (FeedbackEscalation.from_level) ──────────────────
    op.execute("ALTER TYPE grm_from_level RENAME VALUE 'LGA_PIU' TO 'lga_grm_unit'")
    op.execute("ALTER TYPE grm_from_level RENAME VALUE 'PCU' TO 'coordinating_unit'")

    # ── grm_to_level enum (FeedbackEscalation.to_level) ──────────────────────
    op.execute("ALTER TYPE grm_to_level RENAME VALUE 'LGA_PIU' TO 'lga_grm_unit'")
    op.execute("ALTER TYPE grm_to_level RENAME VALUE 'PCU' TO 'coordinating_unit'")


def downgrade() -> None:
    # ── grm_to_level enum ─────────────────────────────────────────────────────
    op.execute("ALTER TYPE grm_to_level RENAME VALUE 'coordinating_unit' TO 'PCU'")
    op.execute("ALTER TYPE grm_to_level RENAME VALUE 'lga_grm_unit' TO 'LGA_PIU'")

    # ── grm_from_level enum ───────────────────────────────────────────────────
    op.execute("ALTER TYPE grm_from_level RENAME VALUE 'coordinating_unit' TO 'PCU'")
    op.execute("ALTER TYPE grm_from_level RENAME VALUE 'lga_grm_unit' TO 'LGA_PIU'")

    # ── committee_level enum ──────────────────────────────────────────────────
    op.execute("ALTER TYPE committee_level RENAME VALUE 'coordinating_unit' TO 'PCU'")
    op.execute("ALTER TYPE committee_level RENAME VALUE 'lga_grm_unit' TO 'LGA_PIU'")

    # ── grm_level enum ────────────────────────────────────────────────────────
    op.execute("ALTER TYPE grm_level RENAME VALUE 'coordinating_unit' TO 'PCU'")
    op.execute("ALTER TYPE grm_level RENAME VALUE 'lga_grm_unit' TO 'LGA_PIU'")

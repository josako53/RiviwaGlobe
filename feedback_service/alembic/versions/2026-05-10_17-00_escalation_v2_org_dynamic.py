"""Escalation v2 — fully org-dynamic paths with template library.

Revision ID: a1b2c3d4e5f6
Revises: f1a2b3c4d5e6
Create Date: 2026-05-10 17:00:00

WHY
───
Each organisation registered in Riviwa has a completely different internal
structure. The previous system had one system template (TARURA/TANROADS roads
agency chain) and fell back to it for every org — making escalation irrelevant
for hospitals, telecoms, NGOs, corporates, etc.

This migration:
  1. Adds template_key to escalation_paths — records which built-in template
     a path was created from (informational, used in the template catalogue UI).
  2. Adds applies_to_feedback_types (JSONB) to escalation_paths — allows an org
     to have one path for grievances and a different (shorter) one for suggestions.
  3. Adds responsible_org_unit (JSONB) to escalation_levels — soft links each
     level to the org's actual departments, branches, users, or committees.
  4. Adds consumer_visible_name to escalation_levels — what the submitter sees
     when their feedback is at this level (hides internal org structure terms).
  5. Back-fills template_key='GOVT_GRM_STANDARD' on the existing system template
     so it can be found by the new key-based lookup.

New service behaviour (escalation_service.py + escalation_repository.py):
  · seed_system_templates() now seeds SIX templates instead of one.
  · resolve_path_for_project() NO LONGER falls back to the TARURA template.
    If an org has no default path, it returns None (no escalation configured).
  · New endpoint: POST /escalation-paths/quick-setup — one-call wizard.
  · New endpoint: GET /escalation-paths/available-templates — template catalogue.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision      = "9e8d7c6b5a49"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    # ── escalation_paths: new columns ────────────────────────────────────────
    op.add_column(
        "escalation_paths",
        sa.Column("template_key", sa.String(50), nullable=True),
    )
    op.add_column(
        "escalation_paths",
        sa.Column("applies_to_feedback_types", JSONB, nullable=True),
    )
    op.create_index(
        "ix_escalation_paths_template_key",
        "escalation_paths", ["template_key"],
    )

    # ── escalation_levels: new columns ───────────────────────────────────────
    op.add_column(
        "escalation_levels",
        sa.Column("responsible_org_unit", JSONB, nullable=True),
    )
    op.add_column(
        "escalation_levels",
        sa.Column("consumer_visible_name", sa.String(255), nullable=True),
    )

    # ── Back-fill the existing TARURA/TANROADS system template ────────────────
    # The old template was seeded without a template_key. Give it the key that
    # matches the new GOVT_GRM_STANDARD seed so key-based lookups work.
    op.execute("""
        UPDATE escalation_paths
        SET    template_key = 'GOVT_GRM_STANDARD'
        WHERE  is_system_template = true
          AND  template_key IS NULL
          AND  name ILIKE '%TARURA%'
    """)


def downgrade() -> None:
    op.drop_index("ix_escalation_paths_template_key", table_name="escalation_paths")
    op.drop_column("escalation_paths", "applies_to_feedback_types")
    op.drop_column("escalation_paths", "template_key")
    op.drop_column("escalation_levels", "consumer_visible_name")
    op.drop_column("escalation_levels", "responsible_org_unit")

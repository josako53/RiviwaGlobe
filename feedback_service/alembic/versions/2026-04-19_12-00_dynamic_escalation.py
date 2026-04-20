"""dynamic_escalation

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-04-19 12:00:00.000000+00:00

Adds the dynamic per-organisation GRM escalation hierarchy.

New tables:
  escalation_paths  — one configurable chain per org (or system template)
  escalation_levels — ordered steps within a chain

New columns:
  fb_projects.escalation_path_id
  feedbacks.escalation_path_id
  feedbacks.current_level_id
  feedback_escalations.from_level_id
  feedback_escalations.to_level_id

The legacy current_level (GRMLevel enum) and from_level/to_level columns are
preserved untouched for backward compatibility with existing analytics and Spark jobs.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── escalation_paths ──────────────────────────────────────────────────────
    op.create_table(
        "escalation_paths",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("org_id", UUID(as_uuid=True), nullable=True),
        sa.Column(
            "project_id", UUID(as_uuid=True),
            sa.ForeignKey("fb_projects.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_default", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_system_template", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_escalation_paths_org_id",         "escalation_paths", ["org_id"])
    op.create_index("ix_escalation_paths_project_id",     "escalation_paths", ["project_id"])
    op.create_index("ix_escalation_paths_is_default",     "escalation_paths", ["is_default"])
    op.create_index("ix_escalation_paths_is_system",      "escalation_paths", ["is_system_template"])
    op.create_index("ix_escalation_paths_is_active",      "escalation_paths", ["is_active"])
    # Partial unique index: at most one default path per org
    op.execute(
        "CREATE UNIQUE INDEX uq_escalation_path_org_default "
        "ON escalation_paths (org_id, is_default) "
        "WHERE is_default = true"
    )

    # ── escalation_levels ─────────────────────────────────────────────────────
    op.create_table(
        "escalation_levels",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "path_id", UUID(as_uuid=True),
            sa.ForeignKey("escalation_paths.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("level_order", sa.Integer, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_final", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("ack_sla_hours", sa.Integer, nullable=True),
        sa.Column("resolution_sla_hours", sa.Integer, nullable=True),
        sa.Column("sla_overrides", JSONB, nullable=True),
        sa.Column("auto_escalate_on_breach", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("auto_escalate_after_hours", sa.Integer, nullable=True),
        sa.Column("responsible_role", sa.String(100), nullable=True),
        sa.Column("notify_emails", JSONB, nullable=True),
        sa.Column("grm_level_ref", sa.String(30), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("path_id", "level_order", name="uq_escalation_level_order"),
        sa.UniqueConstraint("path_id", "code",        name="uq_escalation_level_code"),
    )
    op.create_index("ix_escalation_levels_path_id",      "escalation_levels", ["path_id"])
    op.create_index("ix_escalation_levels_grm_level_ref","escalation_levels", ["grm_level_ref"])

    # ── fb_projects: escalation_path_id ──────────────────────────────────────
    op.add_column(
        "fb_projects",
        sa.Column("escalation_path_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_fb_projects_escalation_path_id", "fb_projects", ["escalation_path_id"])

    # ── feedbacks: escalation_path_id + current_level_id ─────────────────────
    op.add_column(
        "feedbacks",
        sa.Column("escalation_path_id", UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "feedbacks",
        sa.Column(
            "current_level_id", UUID(as_uuid=True),
            sa.ForeignKey("escalation_levels.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_feedbacks_escalation_path_id",  "feedbacks", ["escalation_path_id"])
    op.create_index("ix_feedbacks_current_level_id",    "feedbacks", ["current_level_id"])

    # ── feedback_escalations: from_level_id + to_level_id ─────────────────────
    op.add_column(
        "feedback_escalations",
        sa.Column(
            "from_level_id", UUID(as_uuid=True),
            sa.ForeignKey("escalation_levels.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "feedback_escalations",
        sa.Column(
            "to_level_id", UUID(as_uuid=True),
            sa.ForeignKey("escalation_levels.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_feedback_escalations_to_level_id", "feedback_escalations", ["to_level_id"])


def downgrade() -> None:
    # feedback_escalations
    op.drop_index("ix_feedback_escalations_to_level_id", table_name="feedback_escalations")
    op.drop_column("feedback_escalations", "to_level_id")
    op.drop_column("feedback_escalations", "from_level_id")

    # feedbacks
    op.drop_index("ix_feedbacks_current_level_id",   table_name="feedbacks")
    op.drop_index("ix_feedbacks_escalation_path_id", table_name="feedbacks")
    op.drop_column("feedbacks", "current_level_id")
    op.drop_column("feedbacks", "escalation_path_id")

    # fb_projects
    op.drop_index("ix_fb_projects_escalation_path_id", table_name="fb_projects")
    op.drop_column("fb_projects", "escalation_path_id")

    # escalation_levels
    op.drop_index("ix_escalation_levels_grm_level_ref", table_name="escalation_levels")
    op.drop_index("ix_escalation_levels_path_id",       table_name="escalation_levels")
    op.drop_table("escalation_levels")

    # escalation_paths
    op.execute("DROP INDEX IF EXISTS uq_escalation_path_org_default")
    op.drop_index("ix_escalation_paths_is_active",  table_name="escalation_paths")
    op.drop_index("ix_escalation_paths_is_system",  table_name="escalation_paths")
    op.drop_index("ix_escalation_paths_is_default", table_name="escalation_paths")
    op.drop_index("ix_escalation_paths_project_id", table_name="escalation_paths")
    op.drop_index("ix_escalation_paths_org_id",     table_name="escalation_paths")
    op.drop_table("escalation_paths")

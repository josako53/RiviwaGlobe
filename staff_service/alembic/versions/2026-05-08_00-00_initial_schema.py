"""initial_schema

Revision ID: b2c3d4e5f6a7
Revises:
Create Date: 2026-05-08 00:00:00.000000+00:00

Creates all staff_service tables:
  - org_cache
  - staff_id_sequences
  - staff_profiles
  - staff_verifications
  - staff_fraud_reports
  - staff_feedbacks
  - bulk_import_jobs
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "b2c3d4e5f6a7"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── org_cache ─────────────────────────────────────────────────────────────
    op.create_table(
        "org_cache",
        sa.Column("org_id", sa.UUID(), primary_key=True),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("slug", sa.String(200), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("synced_at", sa.DateTime(), nullable=False),
    )

    # ── staff_id_sequences ────────────────────────────────────────────────────
    op.create_table(
        "staff_id_sequences",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("last_value", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("org_id", name="uq_staff_id_seq_org"),
    )
    op.create_index("ix_staff_id_sequences_org_id", "staff_id_sequences", ["org_id"])

    # ── staff_profiles ────────────────────────────────────────────────────────
    op.create_table(
        "staff_profiles",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("staff_code", sa.String(30), nullable=False),
        sa.Column("qr_code_id", sa.UUID(), nullable=True),
        sa.Column("badge_number", sa.String(100), nullable=True),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("middle_name", sa.String(100), nullable=True),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("email", sa.String(200), nullable=True),
        sa.Column("position", sa.String(200), nullable=False),
        sa.Column("department", sa.String(200), nullable=True),
        sa.Column("branch_id", sa.UUID(), nullable=True),
        sa.Column("branch_name", sa.String(200), nullable=True),
        sa.Column(
            "supervisor_id",
            sa.UUID(),
            sa.ForeignKey("staff_profiles.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("employment_type", sa.String(20), nullable=False, server_default="FULL_TIME"),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("expertise", pg.JSONB(), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("photo_key", sa.String(500), nullable=True),
        sa.Column("photo_url", sa.String(500), nullable=True),
        sa.Column("id_number", sa.String(100), nullable=True),
        sa.Column("project_ids", pg.JSONB(), nullable=True),
        sa.Column("metadata", pg.JSONB(), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("hire_date", sa.Date(), nullable=True),
        sa.Column("suspension_reason", sa.Text(), nullable=True),
        sa.Column("termination_reason", sa.Text(), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("org_id", "staff_code", name="uq_sp_org_code"),
    )
    op.create_index("ix_sp_org_id", "staff_profiles", ["org_id"])
    op.create_index("ix_sp_status", "staff_profiles", ["status"])
    op.create_index("ix_sp_department", "staff_profiles", ["department"])
    op.create_index("ix_sp_branch_id", "staff_profiles", ["branch_id"])
    op.create_index("ix_sp_supervisor_id", "staff_profiles", ["supervisor_id"])

    # ── staff_verifications ───────────────────────────────────────────────────
    op.create_table(
        "staff_verifications",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("lookup_code", sa.String(50), nullable=False),
        sa.Column(
            "staff_id",
            sa.UUID(),
            sa.ForeignKey("staff_profiles.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("org_id", sa.UUID(), nullable=True),
        sa.Column("result", sa.String(20), nullable=False),
        sa.Column("scanner_lat", sa.Float(), nullable=True),
        sa.Column("scanner_lng", sa.Float(), nullable=True),
        sa.Column("scanner_ip", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("verified_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_sv_lookup_code", "staff_verifications", ["lookup_code"])
    op.create_index("ix_sv_org_id", "staff_verifications", ["org_id"])
    op.create_index("ix_sv_result", "staff_verifications", ["result"])
    op.create_index("ix_sv_verified_at", "staff_verifications", ["verified_at"])

    # ── staff_fraud_reports ───────────────────────────────────────────────────
    op.create_table(
        "staff_fraud_reports",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "verification_event_id",
            sa.UUID(),
            sa.ForeignKey("staff_verifications.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("org_id", sa.UUID(), nullable=True),
        sa.Column("reporter_name", sa.String(200), nullable=True),
        sa.Column("reporter_phone", sa.String(20), nullable=True),
        sa.Column("reporter_email", sa.String(200), nullable=True),
        sa.Column("claimed_staff_name", sa.String(200), nullable=True),
        sa.Column("claimed_staff_id", sa.String(100), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("photo_keys", pg.JSONB(), nullable=True),
        sa.Column("photo_urls", pg.JSONB(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="SUBMITTED"),
        sa.Column("ai_analysis", pg.JSONB(), nullable=True),
        sa.Column("assigned_agent_id", sa.UUID(), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_sfr_org_id", "staff_fraud_reports", ["org_id"])
    op.create_index("ix_sfr_created_at", "staff_fraud_reports", ["created_at"])

    # ── staff_feedbacks ───────────────────────────────────────────────────────
    op.create_table(
        "staff_feedbacks",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "verification_event_id",
            sa.UUID(),
            sa.ForeignKey("staff_verifications.id"),
            nullable=False,
        ),
        sa.Column(
            "staff_id",
            sa.UUID(),
            sa.ForeignKey("staff_profiles.id"),
            nullable=False,
        ),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("service_type", sa.String(200), nullable=True),
        sa.Column("location_description", sa.String(500), nullable=True),
        sa.Column("location_lat", sa.Float(), nullable=True),
        sa.Column("location_lng", sa.Float(), nullable=True),
        sa.Column("is_anonymous", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("submitter_name", sa.String(200), nullable=True),
        sa.Column("submitter_phone", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_sf_verification_event_id", "staff_feedbacks", ["verification_event_id"])
    op.create_index("ix_sf_staff_id", "staff_feedbacks", ["staff_id"])
    op.create_index("ix_sf_org_id", "staff_feedbacks", ["org_id"])
    op.create_index("ix_sf_created_at", "staff_feedbacks", ["created_at"])

    # ── bulk_import_jobs ──────────────────────────────────────────────────────
    op.create_table(
        "bulk_import_jobs",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("imported_by", sa.UUID(), nullable=True),
        sa.Column("file_key", sa.String(500), nullable=False),
        sa.Column("original_filename", sa.String(300), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("total_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("successful_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("errors", pg.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_bij_org_id", "bulk_import_jobs", ["org_id"])


def downgrade() -> None:
    for tbl in [
        "bulk_import_jobs",
        "staff_feedbacks",
        "staff_fraud_reports",
        "staff_verifications",
        "staff_profiles",
        "staff_id_sequences",
        "org_cache",
    ]:
        op.drop_table(tbl)

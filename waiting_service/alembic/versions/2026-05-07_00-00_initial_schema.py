"""Initial schema for waiting_service.

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-05-07 00:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "a1b2c3d4e5f6"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "org_cache",
        sa.Column("org_id",    UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name",      sa.String(300), nullable=False),
        sa.Column("slug",      sa.String(200), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("synced_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "service_points",
        sa.Column("id",                  UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("org_id",              UUID(as_uuid=True), nullable=False),
        sa.Column("name",                sa.String(200), nullable=False),
        sa.Column("code",                sa.String(30), nullable=False),
        sa.Column("description",         sa.Text(), nullable=True),
        sa.Column("point_type",          sa.String(20), nullable=False),
        sa.Column("max_concurrent_staff",sa.Integer(), nullable=False, server_default="1"),
        sa.Column("avg_service_minutes", sa.Float(), nullable=False, server_default="5.0"),
        sa.Column("is_active",           sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("org_id", "code", name="uq_service_point_org_code"),
    )
    op.create_index("ix_sp_org_id", "service_points", ["org_id"])
    op.create_index("ix_sp_is_active", "service_points", ["is_active"])

    op.create_table(
        "service_flows",
        sa.Column("id",          UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("org_id",      UUID(as_uuid=True), nullable=False),
        sa.Column("name",        sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active",   sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_default",  sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at",  sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at",  sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_sf_org_id", "service_flows", ["org_id"])
    op.create_index("ix_sf_is_active", "service_flows", ["is_active"])

    op.create_table(
        "flow_steps",
        sa.Column("id",               UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("flow_id",          UUID(as_uuid=True), nullable=False),
        sa.Column("service_point_id", UUID(as_uuid=True), nullable=False),
        sa.Column("step_order",       sa.Integer(), nullable=False),
        sa.Column("is_optional",      sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at",       sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["flow_id"],          ["service_flows.id"],  ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["service_point_id"], ["service_points.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("flow_id", "step_order", name="uq_flow_step_order"),
    )
    op.create_index("ix_fstep_flow_id", "flow_steps", ["flow_id"])

    op.create_table(
        "queue_tickets",
        sa.Column("id",                       UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("org_id",                   UUID(as_uuid=True), nullable=False),
        sa.Column("ticket_number",            sa.String(50), nullable=False, unique=True),
        sa.Column("external_id",              sa.String(200), nullable=True),
        sa.Column("phone_number",             sa.String(20), nullable=True),
        sa.Column("submitter_name",           sa.String(200), nullable=True),
        sa.Column("flow_id",                  UUID(as_uuid=True), nullable=False),
        sa.Column("current_service_point_id", UUID(as_uuid=True), nullable=False),
        sa.Column("current_step_order",       sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status",   sa.String(20), nullable=False, server_default="WAITING"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("channel",  sa.String(20), nullable=False, server_default="KIOSK"),
        sa.Column("notes",    sa.Text(), nullable=True),
        sa.Column("eta_minutes", sa.Float(), nullable=True),
        sa.Column("created_at",   sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at",   sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["flow_id"],                  ["service_flows.id"],   ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["current_service_point_id"], ["service_points.id"],  ondelete="RESTRICT"),
    )
    op.create_index("ix_qt_org_id",    "queue_tickets", ["org_id"])
    op.create_index("ix_qt_status",    "queue_tickets", ["status"])
    op.create_index("ix_qt_priority",  "queue_tickets", ["priority"])
    op.create_index("ix_qt_created_at","queue_tickets", ["created_at"])
    op.create_index("ix_qt_sp_id",     "queue_tickets", ["current_service_point_id"])

    op.create_table(
        "staff_counters",
        sa.Column("id",                UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("org_id",            UUID(as_uuid=True), nullable=False),
        sa.Column("service_point_id",  UUID(as_uuid=True), nullable=False),
        sa.Column("name",              sa.String(150), nullable=False),
        sa.Column("code",              sa.String(20), nullable=False),
        sa.Column("user_id",           UUID(as_uuid=True), nullable=True),
        sa.Column("is_active",         sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("current_ticket_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["service_point_id"],  ["service_points.id"],  ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["current_ticket_id"], ["queue_tickets.id"],   ondelete="SET NULL"),
        sa.UniqueConstraint("service_point_id", "code", name="uq_sc_point_code"),
    )
    op.create_index("ix_sc_org_id", "staff_counters", ["org_id"])
    op.create_index("ix_sc_is_active", "staff_counters", ["is_active"])

    op.create_table(
        "queue_ticket_stages",
        sa.Column("id",               UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("ticket_id",        UUID(as_uuid=True), nullable=False),
        sa.Column("service_point_id", UUID(as_uuid=True), nullable=False),
        sa.Column("step_order",       sa.Integer(), nullable=False),
        sa.Column("staff_counter_id", UUID(as_uuid=True), nullable=True),
        sa.Column("assigned_staff_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("status",           sa.String(20), nullable=False, server_default="WAITING"),
        sa.Column("entered_queue_at",     sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("attending_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at",          sa.DateTime(timezone=True), nullable=True),
        sa.Column("wait_duration_seconds",    sa.Float(), nullable=True),
        sa.Column("service_duration_seconds", sa.Float(), nullable=True),
        sa.Column("notes_by_staff", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["ticket_id"],        ["queue_tickets.id"],   ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["service_point_id"], ["service_points.id"],  ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["staff_counter_id"], ["staff_counters.id"],  ondelete="SET NULL"),
    )
    op.create_index("ix_qts_ticket_id",        "queue_ticket_stages", ["ticket_id"])
    op.create_index("ix_qts_service_point_id", "queue_ticket_stages", ["service_point_id"])
    op.create_index("ix_qts_status",           "queue_ticket_stages", ["status"])

    op.create_table(
        "urgency_requests",
        sa.Column("id",                   UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("ticket_id",            UUID(as_uuid=True), nullable=False),
        sa.Column("org_id",               UUID(as_uuid=True), nullable=False),
        sa.Column("requested_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("urgency_type",         sa.String(30), nullable=False),
        sa.Column("evidence_notes",       sa.Text(), nullable=True),
        sa.Column("status",               sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("reviewed_by_user_id",  UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at",          sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewer_notes",       sa.Text(), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at",   sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["ticket_id"], ["queue_tickets.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_ur_ticket_id", "urgency_requests", ["ticket_id"])
    op.create_index("ix_ur_org_id",    "urgency_requests", ["org_id"])
    op.create_index("ix_ur_status",    "urgency_requests", ["status"])

    op.create_table(
        "staff_sessions",
        sa.Column("id",                  UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("org_id",              UUID(as_uuid=True), nullable=False),
        sa.Column("staff_user_id",       UUID(as_uuid=True), nullable=True),
        sa.Column("staff_counter_id",    UUID(as_uuid=True), nullable=False),
        sa.Column("service_point_id",    UUID(as_uuid=True), nullable=False),
        sa.Column("opened_at",           sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("closed_at",           sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active",           sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("tickets_served",      sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_service_seconds", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["staff_counter_id"], ["staff_counters.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_ss_org_id", "staff_sessions", ["org_id"])
    op.create_index("ix_ss_is_active", "staff_sessions", ["is_active"])

    op.create_table(
        "waiting_ticket_sequences",
        sa.Column("id",         sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("org_id",     UUID(as_uuid=True), nullable=False),
        sa.Column("date",       sa.Date(), nullable=False),
        sa.Column("last_value", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("org_id", "date", name="uq_sequence_org_date"),
    )


def downgrade() -> None:
    op.drop_table("waiting_ticket_sequences")
    op.drop_table("staff_sessions")
    op.drop_table("urgency_requests")
    op.drop_table("queue_ticket_stages")
    op.drop_table("staff_counters")
    op.drop_table("queue_tickets")
    op.drop_table("flow_steps")
    op.drop_table("service_flows")
    op.drop_table("service_points")
    op.drop_table("org_cache")

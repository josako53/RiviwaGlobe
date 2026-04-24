"""Initial integration service tables

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-04-24 12:00:00.000000

"""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "a1b2c3d4e5f6"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── integration_clients ───────────────────────────────────────────────────
    op.create_table(
        "integration_clients",
        sa.Column("id",                     UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("client_id",              sa.String(64),  nullable=False, unique=True),
        sa.Column("client_secret_hash",     sa.String(256), nullable=False),
        sa.Column("name",                   sa.String(200), nullable=False),
        sa.Column("description",            sa.Text,        nullable=True),
        sa.Column("client_type",            sa.String(32),  nullable=False, server_default="API"),
        sa.Column("environment",            sa.String(16),  nullable=False, server_default="SANDBOX"),
        sa.Column("organisation_id",        UUID(as_uuid=True), nullable=True),
        sa.Column("allowed_scopes",         JSONB, nullable=False, server_default="[]"),
        sa.Column("allowed_origins",        JSONB, nullable=False, server_default="[]"),
        sa.Column("allowed_ips",            JSONB, nullable=False, server_default="[]"),
        sa.Column("redirect_uris",          JSONB, nullable=False, server_default="[]"),
        sa.Column("webhook_url",            sa.String(2048), nullable=True),
        sa.Column("webhook_secret_hash",    sa.String(256),  nullable=True),
        sa.Column("webhook_events",         JSONB, nullable=False, server_default="[]"),
        sa.Column("data_endpoint_url",      sa.String(2048), nullable=True),
        sa.Column("data_endpoint_auth_type", sa.String(50),  nullable=True),
        sa.Column("data_endpoint_auth_enc", sa.Text,         nullable=True),
        sa.Column("rate_limit_per_minute",  sa.Integer, nullable=False, server_default="60"),
        sa.Column("rate_limit_per_day",     sa.Integer, nullable=False, server_default="10000"),
        sa.Column("require_mtls",           sa.Boolean, nullable=False, server_default="false"),
        sa.Column("mtls_cert_fingerprint",  sa.String(128), nullable=True),
        sa.Column("is_active",              sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at",             sa.DateTime, nullable=False),
        sa.Column("updated_at",             sa.DateTime, nullable=False),
        sa.Column("last_used_at",           sa.DateTime, nullable=True),
    )
    op.create_index("ix_integration_clients_client_id", "integration_clients", ["client_id"])
    op.create_index("ix_integration_clients_org_id",    "integration_clients", ["organisation_id"])
    op.create_index("ix_integration_clients_env",       "integration_clients", ["environment"])

    # ── integration_api_keys ──────────────────────────────────────────────────
    op.create_table(
        "integration_api_keys",
        sa.Column("id",           UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("client_id",    UUID(as_uuid=True), sa.ForeignKey("integration_clients.id"), nullable=False),
        sa.Column("key_prefix",   sa.String(16),  nullable=False),
        sa.Column("key_hash",     sa.String(256), nullable=False, unique=True),
        sa.Column("name",         sa.String(100), nullable=True),
        sa.Column("scopes",       JSONB, nullable=False, server_default="[]"),
        sa.Column("is_active",    sa.Boolean, nullable=False, server_default="true"),
        sa.Column("expires_at",   sa.DateTime, nullable=True),
        sa.Column("last_used_at", sa.DateTime, nullable=True),
        sa.Column("created_at",   sa.DateTime, nullable=False),
        sa.Column("revoked_at",   sa.DateTime, nullable=True),
    )
    op.create_index("ix_integration_api_keys_client_id", "integration_api_keys", ["client_id"])
    op.create_index("ix_integration_api_keys_key_hash",  "integration_api_keys", ["key_hash"])

    # ── oauth_authorization_codes ─────────────────────────────────────────────
    op.create_table(
        "oauth_authorization_codes",
        sa.Column("id",                     UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("client_id",              UUID(as_uuid=True), sa.ForeignKey("integration_clients.id"), nullable=False),
        sa.Column("code_hash",              sa.String(256), nullable=False, unique=True),
        sa.Column("redirect_uri",           sa.String(2048), nullable=False),
        sa.Column("scopes",                 JSONB, nullable=False, server_default="[]"),
        sa.Column("code_challenge",         sa.String(256), nullable=False),
        sa.Column("code_challenge_method",  sa.String(10),  nullable=False, server_default="S256"),
        sa.Column("user_id",                UUID(as_uuid=True), nullable=True),
        sa.Column("expires_at",             sa.DateTime, nullable=False),
        sa.Column("used_at",                sa.DateTime, nullable=True),
        sa.Column("created_at",             sa.DateTime, nullable=False),
    )
    op.create_index("ix_oauth_auth_codes_client_id", "oauth_authorization_codes", ["client_id"])
    op.create_index("ix_oauth_auth_codes_expires",   "oauth_authorization_codes", ["expires_at"])

    # ── oauth_tokens ──────────────────────────────────────────────────────────
    op.create_table(
        "oauth_tokens",
        sa.Column("id",                  UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("jti",                 sa.String(64),  nullable=False, unique=True),
        sa.Column("client_id",           UUID(as_uuid=True), sa.ForeignKey("integration_clients.id"), nullable=False),
        sa.Column("user_id",             UUID(as_uuid=True), nullable=True),
        sa.Column("grant_type",          sa.String(32),  nullable=False),
        sa.Column("scopes",              JSONB, nullable=False, server_default="[]"),
        sa.Column("refresh_token_hash",  sa.String(256), nullable=True),
        sa.Column("refresh_expires_at",  sa.DateTime,    nullable=True),
        sa.Column("expires_at",          sa.DateTime,    nullable=False),
        sa.Column("revoked_at",          sa.DateTime,    nullable=True),
        sa.Column("created_at",          sa.DateTime,    nullable=False),
    )
    op.create_index("ix_oauth_tokens_jti",      "oauth_tokens", ["jti"])
    op.create_index("ix_oauth_tokens_client_id", "oauth_tokens", ["client_id"])
    op.create_index("ix_oauth_tokens_expires",  "oauth_tokens", ["expires_at"])
    op.create_index("ix_oauth_tokens_revoked",  "oauth_tokens", ["revoked_at"])

    # ── context_sessions ──────────────────────────────────────────────────────
    op.create_table(
        "context_sessions",
        sa.Column("id",                   UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("client_id",            UUID(as_uuid=True), sa.ForeignKey("integration_clients.id"), nullable=False),
        sa.Column("token_hash",           sa.String(256), nullable=False, unique=True),
        sa.Column("pre_filled_data_enc",  sa.Text, nullable=False),
        sa.Column("project_id",           UUID(as_uuid=True), nullable=True),
        sa.Column("org_id",               UUID(as_uuid=True), nullable=True),
        sa.Column("expires_at",           sa.DateTime, nullable=False),
        sa.Column("consumed_at",          sa.DateTime, nullable=True),
        sa.Column("created_at",           sa.DateTime, nullable=False),
    )
    op.create_index("ix_context_sessions_client_id", "context_sessions", ["client_id"])
    op.create_index("ix_context_sessions_token",     "context_sessions", ["token_hash"])
    op.create_index("ix_context_sessions_expires",   "context_sessions", ["expires_at"])

    # ── webhook_deliveries ────────────────────────────────────────────────────
    op.create_table(
        "webhook_deliveries",
        sa.Column("id",               UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("client_id",        UUID(as_uuid=True), sa.ForeignKey("integration_clients.id"), nullable=False),
        sa.Column("event_type",       sa.String(100), nullable=False),
        sa.Column("payload",          JSONB, nullable=False),
        sa.Column("status",           sa.String(16),  nullable=False, server_default="PENDING"),
        sa.Column("attempt_count",    sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_status_code", sa.Integer, nullable=True),
        sa.Column("last_error",       sa.Text, nullable=True),
        sa.Column("next_retry_at",    sa.DateTime, nullable=True),
        sa.Column("delivered_at",     sa.DateTime, nullable=True),
        sa.Column("failed_at",        sa.DateTime, nullable=True),
        sa.Column("created_at",       sa.DateTime, nullable=False),
    )
    op.create_index("ix_webhook_deliveries_client_id",  "webhook_deliveries", ["client_id"])
    op.create_index("ix_webhook_deliveries_event_type", "webhook_deliveries", ["event_type"])
    op.create_index("ix_webhook_deliveries_status",     "webhook_deliveries", ["status"])
    op.create_index("ix_webhook_deliveries_retry",      "webhook_deliveries", ["next_retry_at"])

    # ── integration_audit_logs ────────────────────────────────────────────────
    op.create_table(
        "integration_audit_logs",
        sa.Column("id",          UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("client_id",   UUID(as_uuid=True), sa.ForeignKey("integration_clients.id"), nullable=True),
        sa.Column("method",      sa.String(10),  nullable=False),
        sa.Column("path",        sa.String(512), nullable=False),
        sa.Column("status_code", sa.Integer, nullable=False),
        sa.Column("duration_ms", sa.Integer, nullable=False),
        sa.Column("ip_address",  sa.String(64),  nullable=True),
        sa.Column("user_agent",  sa.String(512), nullable=True),
        sa.Column("auth_method", sa.String(32),  nullable=True),
        sa.Column("timestamp",   sa.DateTime, nullable=False),
    )
    op.create_index("ix_audit_logs_client_id",        "integration_audit_logs", ["client_id"])
    op.create_index("ix_audit_logs_timestamp",        "integration_audit_logs", ["timestamp"])
    op.create_index("ix_audit_logs_client_timestamp", "integration_audit_logs", ["client_id", "timestamp"])


def downgrade() -> None:
    op.drop_table("integration_audit_logs")
    op.drop_table("webhook_deliveries")
    op.drop_table("context_sessions")
    op.drop_table("oauth_tokens")
    op.drop_table("oauth_authorization_codes")
    op.drop_table("integration_api_keys")
    op.drop_table("integration_clients")

"""
models/integration.py — All integration service DB models.

Tables
──────
  integration_clients     — registered partner apps / SDK consumers
  integration_api_keys    — hashed API keys per client
  oauth_authorization_codes — PKCE authorization codes (single-use, 10 min TTL)
  oauth_tokens            — issued access + refresh tokens
  context_sessions        — pre-filled user context (phone/name/service) from partner
  webhook_deliveries      — outbound webhook delivery log with retry state
  integration_audit_logs  — immutable audit trail for every API call
"""
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, Index, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel


# ── Enums ─────────────────────────────────────────────────────────────────────

class ClientType(str, Enum):
    MINI_APP   = "MINI_APP"    # embedded mini-app in partner's mobile app
    WEB_WIDGET = "WEB_WIDGET"  # JS widget / tag on partner website
    API        = "API"         # direct server-to-server API integration
    SDK        = "SDK"         # official Riviwa SDK (React Native / Flutter)
    CHATBOT    = "CHATBOT"     # AI chatbot tag (like Google Tag in Bolt/Uber)


class ClientEnvironment(str, Enum):
    LIVE    = "LIVE"
    SANDBOX = "SANDBOX"


class TokenGrantType(str, Enum):
    AUTHORIZATION_CODE  = "AUTHORIZATION_CODE"
    CLIENT_CREDENTIALS  = "CLIENT_CREDENTIALS"
    REFRESH_TOKEN       = "REFRESH_TOKEN"


class WebhookEventType(str, Enum):
    FEEDBACK_SUBMITTED    = "feedback.submitted"
    FEEDBACK_ACKNOWLEDGED = "feedback.acknowledged"
    FEEDBACK_IN_REVIEW    = "feedback.in_review"
    FEEDBACK_ESCALATED    = "feedback.escalated"
    FEEDBACK_RESOLVED     = "feedback.resolved"
    FEEDBACK_CLOSED       = "feedback.closed"
    FEEDBACK_DISMISSED    = "feedback.dismissed"


class DeliveryStatus(str, Enum):
    PENDING   = "PENDING"
    DELIVERED = "DELIVERED"
    FAILED    = "FAILED"
    RETRYING  = "RETRYING"


# ── IntegrationClient ─────────────────────────────────────────────────────────

class IntegrationClient(SQLModel, table=True):
    """
    A registered third-party partner that integrates with Riviwa.

    Security model:
      client_id        — public identifier, safe to share
      client_secret_hash — bcrypt hash, shown once at creation
      api_key_prefix   — first 8 chars of the active API key (for display)
      signing_secret_hash — HMAC secret for webhook payload signing
      allowed_origins  — CORS allowlist (empty = all origins)
      allowed_ips      — IP allowlist (empty = all IPs; use for banks/hospitals)
      require_mtls     — if true, requests must present a client TLS certificate
    """
    __tablename__ = "integration_clients"

    id:         uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    client_id:  str       = Field(unique=True, index=True, max_length=64,
                                  description="Public OAuth2 client_id, e.g. rwi_client_xxx")
    client_secret_hash: str = Field(max_length=256, description="bcrypt hash of client_secret")

    name:        str           = Field(max_length=200)
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    client_type: ClientType    = Field(default=ClientType.API)
    environment: ClientEnvironment = Field(default=ClientEnvironment.SANDBOX)

    # Owning organisation (soft FK — org lives in auth_db)
    organisation_id: Optional[uuid.UUID] = Field(default=None, index=True)

    # Permitted OAuth2 scopes for this client
    # e.g. ["feedback:write", "feedback:read", "profile:read"]
    allowed_scopes: List[str] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default="[]"),
    )

    # CORS: list of allowed origins for widget/chatbot embeds
    # Empty list = block all cross-origin; ["*"] = allow all
    allowed_origins: List[str] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default="[]"),
    )

    # IP allowlisting for enterprise clients (banks, hospitals)
    allowed_ips: List[str] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default="[]"),
    )

    # Redirect URIs for Authorization Code flow
    redirect_uris: List[str] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default="[]"),
    )

    # Webhook configuration
    webhook_url:          Optional[str] = Field(default=None, max_length=2048)
    webhook_secret_hash:  Optional[str] = Field(default=None, max_length=256,
                                                  description="bcrypt hash of HMAC signing secret")
    webhook_events: List[str] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default="[]"),
        description="Subscribed webhook event types",
    )

    # External data endpoint — Riviwa calls this to pre-fill user context
    data_endpoint_url:       Optional[str] = Field(default=None, max_length=2048)
    data_endpoint_auth_type: Optional[str] = Field(default=None, max_length=50,
                                                     description="bearer|basic|api_key")
    data_endpoint_auth_enc:  Optional[str] = Field(default=None, sa_column=Column(Text),
                                                    description="AES-256-GCM encrypted credential")

    # Rate limiting (per-minute and per-day request caps)
    rate_limit_per_minute: int = Field(default=60)
    rate_limit_per_day:    int = Field(default=10000)

    # Security options
    require_mtls:         bool = Field(default=False, description="Require mutual TLS for enterprise clients")
    mtls_cert_fingerprint: Optional[str] = Field(default=None, max_length=128)

    # Lifecycle
    is_active:    bool      = Field(default=True)
    created_at:   datetime  = Field(default_factory=lambda: datetime.utcnow())
    updated_at:   datetime  = Field(default_factory=lambda: datetime.utcnow())
    last_used_at: Optional[datetime] = Field(default=None)

    # Relationships
    api_keys:    List["ApiKey"]              = Relationship(back_populates="client")
    tokens:      List["OAuthToken"]          = Relationship(back_populates="client")
    deliveries:  List["WebhookDelivery"]     = Relationship(back_populates="client")
    audit_logs:  List["IntegrationAuditLog"] = Relationship(back_populates="client")

    __table_args__ = (
        Index("ix_integration_clients_org_id", "organisation_id"),
        Index("ix_integration_clients_env", "environment"),
    )


# ── ApiKey ────────────────────────────────────────────────────────────────────

class ApiKey(SQLModel, table=True):
    """
    A hashed API key issued to an IntegrationClient.

    Key format: rwi_live_<48_bytes_base64url>  (shown ONCE at creation)
    Stored:     prefix (first 8 chars) + SHA-256 hash of full key

    Clients may have multiple keys to support rotation:
      1. Issue new key
      2. Migrate to new key
      3. Revoke old key
    """
    __tablename__ = "integration_api_keys"

    id:         uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    client_id:  uuid.UUID = Field(foreign_key="integration_clients.id", index=True)

    key_prefix:  str = Field(max_length=16, description="First 8 chars, safe to display")
    key_hash:    str = Field(max_length=256, unique=True, description="SHA-256 of full key")

    name:    Optional[str]  = Field(default=None, max_length=100, description="Friendly label")
    scopes:  List[str]      = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default="[]"),
        description="Subset of client's allowed_scopes",
    )

    is_active:   bool      = Field(default=True)
    expires_at:  Optional[datetime] = Field(default=None)
    last_used_at: Optional[datetime] = Field(default=None)
    created_at:  datetime  = Field(default_factory=lambda: datetime.utcnow())
    revoked_at:  Optional[datetime] = Field(default=None)

    client: Optional[IntegrationClient] = Relationship(back_populates="api_keys")


# ── OAuthAuthorizationCode ────────────────────────────────────────────────────

class OAuthAuthorizationCode(SQLModel, table=True):
    """
    Short-lived single-use code for Authorization Code + PKCE flow.
    Expires in 10 minutes. Consumed on first use.
    """
    __tablename__ = "oauth_authorization_codes"

    id:         uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    client_id:  uuid.UUID = Field(foreign_key="integration_clients.id", index=True)

    code_hash:    str           = Field(max_length=256, unique=True)
    redirect_uri: str           = Field(max_length=2048)
    scopes:       List[str]     = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default="[]"),
    )

    # PKCE
    code_challenge:        str = Field(max_length=256)
    code_challenge_method: str = Field(default="S256", max_length=10)

    # Linked Riviwa user (set when user authorized via login flow)
    user_id: Optional[uuid.UUID] = Field(default=None, index=True)

    expires_at: datetime = Field()
    used_at:    Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.utcnow())

    __table_args__ = (
        Index("ix_oauth_auth_codes_expires", "expires_at"),
    )


# ── OAuthToken ────────────────────────────────────────────────────────────────

class OAuthToken(SQLModel, table=True):
    """
    Issued access token and optional refresh token.

    Access tokens: short-lived (15 min default), JWT-signed
    Refresh tokens: longer-lived (30 days), opaque, stored as hash
    """
    __tablename__ = "oauth_tokens"

    id:        uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    jti:       str       = Field(max_length=64, unique=True, index=True,
                                 description="JWT ID — used for revocation checks")
    client_id: uuid.UUID = Field(foreign_key="integration_clients.id", index=True)
    user_id:   Optional[uuid.UUID] = Field(default=None, index=True)

    grant_type:    TokenGrantType = Field()
    scopes:        List[str]      = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default="[]"),
    )

    # Refresh token (hashed) — null for client_credentials
    refresh_token_hash: Optional[str] = Field(default=None, max_length=256)
    refresh_expires_at: Optional[datetime] = Field(default=None)

    expires_at:  datetime           = Field(index=True)
    revoked_at:  Optional[datetime] = Field(default=None)
    created_at:  datetime           = Field(default_factory=lambda: datetime.utcnow())

    client: Optional[IntegrationClient] = Relationship(back_populates="tokens")

    __table_args__ = (
        Index("ix_oauth_tokens_revoked", "revoked_at"),
    )


# ── ContextSession ────────────────────────────────────────────────────────────

class ContextSession(SQLModel, table=True):
    """
    Pre-filled user context pushed by a partner before the user starts a
    Riviwa session (mini app / widget / chatbot).

    Allows seamless form entry: partner provides phone, name, service, product,
    category, account_number etc. Riviwa uses these to pre-fill feedback fields.

    Security:
      - session_token is opaque, shown once to partner, stored as SHA-256 hash
      - pre_filled_data is AES-256-GCM encrypted at rest
      - TTL: 30 minutes; consumed once → consumed_at set
    """
    __tablename__ = "context_sessions"

    id:           uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    client_id:    uuid.UUID = Field(foreign_key="integration_clients.id", index=True)
    token_hash:   str       = Field(max_length=256, unique=True, index=True)

    # Encrypted JSON: {phone, name, service_id, product_id, category, account_ref, ...}
    pre_filled_data_enc: str = Field(sa_column=Column(Text),
                                     description="AES-256-GCM encrypted JSON context")

    # Optional: restrict this session to a specific Riviwa project
    project_id: Optional[uuid.UUID] = Field(default=None)
    org_id:     Optional[uuid.UUID] = Field(default=None)

    expires_at:   datetime           = Field(index=True)
    consumed_at:  Optional[datetime] = Field(default=None)
    created_at:   datetime           = Field(default_factory=lambda: datetime.utcnow())

    __table_args__ = (
        Index("ix_context_sessions_expires", "expires_at"),
    )


# ── WebhookDelivery ───────────────────────────────────────────────────────────

class WebhookDelivery(SQLModel, table=True):
    """
    Outbound webhook delivery record.

    Riviwa signs every payload:
      X-Riviwa-Signature: sha256=<HMAC-SHA256(body, client.signing_secret)>
      X-Riviwa-Timestamp: <unix_timestamp>
      X-Riviwa-Event: feedback.submitted

    Retry policy: 3 attempts with exponential backoff (30s, 5m, 30m).
    After 3 failures → status=FAILED, no further retries.
    """
    __tablename__ = "webhook_deliveries"

    id:        uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    client_id: uuid.UUID = Field(foreign_key="integration_clients.id", index=True)

    event_type:    str  = Field(max_length=100, index=True)
    payload:       Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False),
    )

    status:         DeliveryStatus = Field(default=DeliveryStatus.PENDING, index=True)
    attempt_count:  int            = Field(default=0)
    last_status_code: Optional[int] = Field(default=None)
    last_error:     Optional[str]  = Field(default=None, sa_column=Column(Text))

    next_retry_at:  Optional[datetime] = Field(default=None, index=True)
    delivered_at:   Optional[datetime] = Field(default=None)
    failed_at:      Optional[datetime] = Field(default=None)
    created_at:     datetime           = Field(default_factory=lambda: datetime.utcnow())

    client: Optional[IntegrationClient] = Relationship(back_populates="deliveries")

    __table_args__ = (
        Index("ix_webhook_deliveries_retry", "next_retry_at"),
    )


# ── IntegrationAuditLog ───────────────────────────────────────────────────────

class IntegrationAuditLog(SQLModel, table=True):
    """
    Immutable audit trail. Every API call from a partner is logged here.
    Write-once — never updated.
    """
    __tablename__ = "integration_audit_logs"

    id:        uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    client_id: Optional[uuid.UUID] = Field(
        default=None, foreign_key="integration_clients.id", index=True
    )

    method:      str = Field(max_length=10)
    path:        str = Field(max_length=512)
    status_code: int = Field()
    duration_ms: int = Field(description="Request duration in milliseconds")

    ip_address:  Optional[str] = Field(default=None, max_length=64)
    user_agent:  Optional[str] = Field(default=None, max_length=512)
    # Which key or token was used
    auth_method: Optional[str] = Field(default=None, max_length=32,
                                        description="api_key|access_token|client_credentials")

    timestamp: datetime = Field(default_factory=lambda: datetime.utcnow(), index=True)

    client: Optional[IntegrationClient] = Relationship(back_populates="audit_logs")

    __table_args__ = (
        Index("ix_audit_logs_timestamp", "timestamp"),
        Index("ix_audit_logs_client_timestamp", "client_id", "timestamp"),
    )

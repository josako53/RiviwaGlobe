"""
models/fraud.py
─────────────────────────────────────────────────────────────────────────────
Five tables that power the duplicate-account detection system:

  DeviceFingerprint   — one row per (user, browser fingerprint hash)
  IPRecord            — one row per (user, IP address) registration event
  FraudAssessment     — one row per registration attempt, fully scored 0-100
  IDVerification      — government ID verification session lifecycle
  BehavioralSession   — aggregated JS behavioral signals per registration

Key SQLModel patterns used in this file:
  • `sa_column=Column(SAEnum(...))` for Postgres ENUM columns
  • `sa_column=Column(JSONB, ...)`  for Postgres JSONB columns
  • `sa_column=Column(DateTime(timezone=True), onupdate=...)` for updated_at
  • `sa_column=Column(Text, ...)`   for unbounded text (action_reason)
  • All other columns use plain `Field(...)` — SQLModel handles the mapping

Duplicate detection query pattern (DeviceFingerprint):
  SELECT DISTINCT user_id
  FROM device_fingerprints
  WHERE fingerprint_hash = :hash
  → If rowcount > 1: same browser fingerprint used by multiple accounts

Government ID deduplication (IDVerification):
  id_number_hash = blake2b(normalised_id_number)
  Stored permanently with an index.
  SELECT * FROM id_verifications
  WHERE id_number_hash = :hash AND status = 'approved'
  → If found and user_id != current_user: BLOCK registration

Relationship wiring:
  DeviceFingerprint.user  ←back_populates→  User.fingerprints
  FraudAssessment.user    ←back_populates→  User.fraud_assessments
  IDVerification.user     ←back_populates→  User.id_verifications
─────────────────────────────────────────────────────────────────────────────
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import ForeignKey, Column, DateTime, Enum as SAEnum, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from models.user import User


# ══════════════════════════════════════════════════════════════════════════════
# Enums
# ══════════════════════════════════════════════════════════════════════════════

class IDVerificationStatus(str, Enum):
    """Lifecycle of a government ID verification session."""
    PENDING    = "pending"      # session created, user hasn't started yet
    PROCESSING = "processing"   # user submitted docs, provider is checking
    APPROVED   = "approved"     # identity confirmed → activate account
    REJECTED   = "rejected"     # docs failed → user may retry
    EXPIRED    = "expired"      # session timed out → cleaned up by Celery beat


class FraudAction(str, Enum):
    """
    Decision produced by ScoringEngine for a registration attempt.
    Thresholds are configured in .env:
      FRAUD_SCORE_WARN_THRESHOLD    default 30
      FRAUD_SCORE_REVIEW_THRESHOLD  default 50
      FRAUD_SCORE_BLOCK_THRESHOLD   default 80
    """
    ALLOW  = "allow"   # score < WARN   → proceed, send email verification
    WARN   = "warn"    # score >= WARN  → proceed but log and monitor
    REVIEW = "review"  # score >= REVIEW → require government ID before activation
    BLOCK  = "block"   # score >= BLOCK  → hard reject, generic error to user


# ══════════════════════════════════════════════════════════════════════════════
# DeviceFingerprint
# ══════════════════════════════════════════════════════════════════════════════

class DeviceFingerprint(SQLModel, table=True):
    """
    One row per (user_id, fingerprint_hash) combination.

    fingerprint_hash = SHA-256 of:
      canvas_hash + audio_hash + webgl_hash + fonts_hash + screen_hash
      + timezone + user_agent + platform + language + hardware_concurrency

    Duplicate detection:
      If the same fingerprint_hash is linked to two different user_ids
      → high-confidence duplicate account signal.

    `seen_count` tracks how many times this fingerprint was observed
    for this user (helps distinguish occasional VPN switching from
    a fresh device).
    """
    __tablename__ = "device_fingerprints"

    # ── PK ────────────────────────────────────────────────────────────────────
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        nullable=False,
    )

    # ── FK → users ────────────────────────────────────────────────────────────
    user_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )

    # ── Composite fingerprint hash ────────────────────────────────────────────
    fingerprint_hash: str = Field(
        max_length=64,      # SHA-256 hex = exactly 64 chars
        index=True,
        nullable=False,
    )

    # ── Individual component hashes (for ML feature engineering) ─────────────
    canvas_hash:  Optional[str] = Field(default=None, max_length=64, nullable=True)
    audio_hash:   Optional[str] = Field(default=None, max_length=64, nullable=True)
    webgl_hash:   Optional[str] = Field(default=None, max_length=64, nullable=True)
    fonts_hash:   Optional[str] = Field(default=None, max_length=64, nullable=True)
    screen_hash:  Optional[str] = Field(default=None, max_length=64, nullable=True)

    # ── Raw environment signals ───────────────────────────────────────────────
    timezone:   Optional[str] = Field(default=None, max_length=50,  nullable=True)
    user_agent: Optional[str] = Field(default=None, max_length=512, nullable=True)
    language:   Optional[str] = Field(default=None, max_length=20,  nullable=True)
    platform:   Optional[str] = Field(default=None, max_length=50,  nullable=True)

    # ── Bot / anti-detect signals ─────────────────────────────────────────────
    webdriver_detected:   bool = Field(default=False, nullable=False)
    headless_detected:    bool = Field(default=False, nullable=False)
    inconsistencies_count: int = Field(default=0,    nullable=False)

    # ── Usage tracking ────────────────────────────────────────────────────────
    seen_count: int = Field(default=1, nullable=False)

    first_seen: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=text("now()"),
            nullable=False,
        )
    )
    # onupdate keeps last_seen current every time the row is updated via ORM
    last_seen: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=text("now()"),
            onupdate=text("now()"),
            nullable=False,
        )
    )

    # ── Relationship ──────────────────────────────────────────────────────────
    user: Optional["User"] = Relationship(back_populates="fingerprints")


# ══════════════════════════════════════════════════════════════════════════════
# IPRecord
# ══════════════════════════════════════════════════════════════════════════════

class IPRecord(SQLModel, table=True):
    """
    One row per registration event from a given IP address for a given user.

    Stored separately from DeviceFingerprint so we can:
      • Count velocity: registrations from this IP in the last hour
      • Detect shared IPs independently of browser fingerprints
      • Cache geo data (country, VPN flag) without duplicating it everywhere

    NOTE: IPRecord has NO relationship back to User in the ORM because we
    primarily query it by ip_address (not by user_id), and adding a reverse
    relationship would load all IP records whenever User is accessed.
    Use fraud_repository.get_users_by_ip() for lookups.
    """
    __tablename__ = "ip_records"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        nullable=False,
    )

    # FK with CASCADE — IPRecord rows are cleaned up when User is deleted
    user_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )

    # Supports IPv4 (max 15 chars) and IPv6 (max 39 chars) → VARCHAR(45)
    ip_address: str = Field(max_length=45, index=True, nullable=False)

    # ── Geo data from ip-api / MaxMind ────────────────────────────────────────
    country_code: Optional[str] = Field(default=None, max_length=2,   nullable=True)
    region:       Optional[str] = Field(default=None, max_length=100, nullable=True)
    city:         Optional[str] = Field(default=None, max_length=100, nullable=True)
    latitude:     Optional[float] = Field(default=None, nullable=True)
    longitude:    Optional[float] = Field(default=None, nullable=True)
    isp:          Optional[str] = Field(default=None, max_length=200, nullable=True)
    asn:          Optional[str] = Field(default=None, max_length=20,  nullable=True)

    # ── Risk signals (set by geo_service.lookup_ip) ───────────────────────────
    is_vpn:              bool = Field(default=False, nullable=False)
    is_tor:              bool = Field(default=False, nullable=False)
    is_proxy:            bool = Field(default=False, nullable=False)
    is_datacenter:       bool = Field(default=False, nullable=False)
    is_high_risk_country: bool = Field(default=False, nullable=False)

    first_seen: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=text("now()"),
            nullable=False,
        )
    )
    last_seen: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=text("now()"),
            onupdate=text("now()"),
            nullable=False,
        )
    )


# ══════════════════════════════════════════════════════════════════════════════
# FraudAssessment
# ══════════════════════════════════════════════════════════════════════════════

class FraudAssessment(SQLModel, table=True):
    """
    Immutable audit record for every registration attempt.

    Stores a complete snapshot of all signals + the weighted score breakdown
    + the final action taken. Never updated after creation.

    user_id is NULLABLE: when action=BLOCK the registration is rejected
    before a User row is created, so there is no user_id to reference.

    JSONB columns:
      linked_account_ids: {"ids": ["uuid1", "uuid2", ...]}
        → other user accounts that share signals with this attempt

      signal_details: {...}
        → human-readable breakdown for the fraud review admin UI
        → also fed into the ML re-scoring Celery task
    """
    __tablename__ = "fraud_assessments"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        nullable=False,
    )

    # Nullable FK — null when BLOCK action fires before User is written
    user_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("users.id", ondelete="SET NULL"),
            nullable=False,
            index=True,
            default=None,
        ),
    )

    # ── Input signal snapshot ─────────────────────────────────────────────────
    email:            str           = Field(max_length=255, nullable=False)
    email_normalized: str           = Field(max_length=255, nullable=False)
    ip_address:       str           = Field(max_length=45,  nullable=False)
    fingerprint_hash: Optional[str] = Field(default=None, max_length=64, nullable=True)
    phone_number:     Optional[str] = Field(default=None, max_length=20, nullable=True)

    # ── Score breakdown (each 0-100, combined to total_score via weights) ─────
    score_email:       int = Field(default=0, nullable=False)
    score_ip:          int = Field(default=0, nullable=False)
    score_fingerprint: int = Field(default=0, nullable=False)
    score_behavioral:  int = Field(default=0, nullable=False)
    score_velocity:    int = Field(default=0, nullable=False)
    score_geo:         int = Field(default=0, nullable=False)
    total_score:       int = Field(default=0, index=True, nullable=False)

    # ── JSONB columns — must use sa_column for Postgres JSONB type ───────────
    linked_account_ids: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    signal_details: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )

    # ── Action taken ─────────────────────────────────────────────────────────
    # SAEnum stores "allow" / "warn" / "review" / "block" as a Postgres enum.
    # We must use sa_column to specify the enum type name for Alembic.
    action: FraudAction = Field(
        sa_column=Column(
            SAEnum(FraudAction, name="fraud_action"),
            nullable=False,
            index=True,
        )
    )

    # Text (unbounded) for the reason string — needs sa_column
    action_reason: Optional[str] = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
    )

    # FK to the IDVerification session created when action=REVIEW
    # SET NULL: if the IDVerification row is cleaned up, the assessment stays
    id_verification_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(
            ForeignKey("id_verifications.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=text("now()"),
            nullable=False,
        )
    )

    # ── Relationship ──────────────────────────────────────────────────────────
    user: Optional["User"] = Relationship(back_populates="fraud_assessments")


# ══════════════════════════════════════════════════════════════════════════════
# IDVerification
# ══════════════════════════════════════════════════════════════════════════════

class IDVerification(SQLModel, table=True):
    """
    Government ID verification session.

    Critical design choices:
      1. Raw ID number NEVER stored.
         id_number_hash = blake2b(uppercase_stripped_id_number)
         Indexed and used to prevent the same physical ID from being used
         across multiple accounts (permanent deduplication anchor).

      2. provider_session_id is UNIQUE — the external session ID from
         Stripe Identity / Onfido / Persona. Incoming webhooks carry this
         ID so we can look up the right row in O(1).

      3. Status drives user account_status:
           APPROVED  → user.status=ACTIVE, user.id_verified=True
           REJECTED  → user.status stays PENDING_ID (retry allowed)
           EXPIRED   → cleaned up by daily Celery beat task
    """
    __tablename__ = "id_verifications"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        nullable=False,
    )

    user_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )

    # ── Provider metadata ─────────────────────────────────────────────────────
    provider: str = Field(
        max_length=30,
        nullable=False,
        description="stripe | onfido | persona | stub",
    )
    # The key that incoming webhooks carry — must be unique across all sessions
    provider_session_id: str = Field(
        max_length=255,
        unique=True,
        index=True,
        nullable=False,
    )

    # ── Session status ────────────────────────────────────────────────────────
    status: IDVerificationStatus = Field(
        default=IDVerificationStatus.PENDING,
        sa_column=Column(
            SAEnum(IDVerificationStatus, name="id_verification_status"),
            nullable=False,
            index=True,
        ),
    )

    # ── Permanently retained data (hashed — raw values never stored) ──────────
    # BLAKE2b(normalised_id_number) — 64 hex chars, indexed for fast dedup check
    id_number_hash: Optional[str] = Field(
        default=None,
        max_length=64,
        index=True,
        nullable=True,
        description="BLAKE2b hash of the normalised government ID number",
    )
    id_type: Optional[str] = Field(
        default=None,
        max_length=30,
        nullable=True,
        description="passport | national_id | drivers_license",
    )
    id_country:      Optional[str]  = Field(default=None, max_length=2,   nullable=True)
    name_match:      Optional[bool] = Field(default=None, nullable=True)
    dob_match:       Optional[bool] = Field(default=None, nullable=True)
    rejection_reason: Optional[str] = Field(default=None, max_length=255, nullable=True)

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=text("now()"),
            nullable=False,
        )
    )
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=text("now()"),
            onupdate=text("now()"),
            nullable=False,
        )
    )
    expires_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )

    # ── Relationship ──────────────────────────────────────────────────────────
    user: Optional["User"] = Relationship(back_populates="id_verifications")


# ══════════════════════════════════════════════════════════════════════════════
# BehavioralSession
# ══════════════════════════════════════════════════════════════════════════════

class BehavioralSession(SQLModel, table=True):
    """
    Per-registration behavioral summary collected by frontend/fraud-collector.js.

    Raw events (every keydown, mousemove) are NOT stored here — they are
    computed client-side and only the summary is posted to the API.

    session_token:
      Issued by the JS collector on page load.
      Sent with every event so the backend can group them.
      Linked to user_id once the registration form is submitted.

    ML scoring:
      ml_bot_probability and behavioral_score are NULL at creation.
      They are populated by the score_behavioral_ml Celery task
      that runs asynchronously after registration completes.

    No relationship to User here by design:
      BehavioralSession is queried by session_token, not by user_id.
      A reverse User.behavioral_sessions relationship would cause all
      sessions to load whenever a User is fetched.
    """
    __tablename__ = "behavioral_sessions"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        nullable=False,
    )

    # Issued on page load by JS; links pre-submit events to the registration
    session_token: str = Field(
        max_length=64,
        unique=True,
        index=True,
        nullable=False,
    )

    # Null until registration form submitted and user row created
    user_id: Optional[uuid.UUID] = Field(
        default=None,
        nullable=True,
        index=True,
    )

    # ── Typing dynamics ───────────────────────────────────────────────────────
    typing_speed_avg_ms:  Optional[float] = Field(default=None, nullable=True)
    typing_speed_stddev:  Optional[float] = Field(default=None, nullable=True)
    paste_detected:       bool = Field(default=False, nullable=False)
    autofill_detected:    bool = Field(default=False, nullable=False)
    copy_detected:        bool = Field(default=False, nullable=False)
    field_focus_count:    int  = Field(default=0,     nullable=False)
    field_blur_count:     int  = Field(default=0,     nullable=False)

    # ── Mouse / touch dynamics ────────────────────────────────────────────────
    mouse_movement_count: int           = Field(default=0,    nullable=False)
    click_count:          int           = Field(default=0,    nullable=False)
    scroll_depth_pct:     Optional[float] = Field(default=None, nullable=True)
    touch_device:         bool          = Field(default=False, nullable=False)
    hesitation_pauses:    int           = Field(default=0,    nullable=False)

    # ── Form timing ───────────────────────────────────────────────────────────
    form_time_seconds:      Optional[float] = Field(default=None, nullable=True)
    form_completion_ratio:  Optional[float] = Field(default=None, nullable=True)

    # ── Suspicion flags ───────────────────────────────────────────────────────
    devtools_opened:   bool = Field(default=False, nullable=False)
    tab_hidden_count:  int  = Field(default=0,     nullable=False)
    # True when form_time_seconds < 3 — humans cannot fill forms that fast
    rapid_completion:  bool = Field(default=False, nullable=False)

    # ── ML output (populated by Celery task score_behavioral_ml) ─────────────
    ml_bot_probability: Optional[float] = Field(default=None, nullable=True)
    behavioral_score:   Optional[int]   = Field(default=None, nullable=True)

    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=text("now()"),
            nullable=False,
        )
    )
    scored_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )

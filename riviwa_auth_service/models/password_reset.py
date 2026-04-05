"""
models/password_reset.py
─────────────────────────────────────────────────────────────────────────────
Hashed one-time tokens for password reset, sent via email or SMS.

Security design decisions:
  • We store ONLY sha256(raw_token). The raw token is emailed/SMS'd to
    the user and is never written to the DB. Even if the DB leaks, tokens
    cannot be replayed.
  • `used_at` is set the instant a token is consumed. A second use of the
    same token will find used_at IS NOT NULL and reject immediately.
  • `expires_at` has a short window (1 hour). is_valid() enforces both.
  • The repository invalidates all previous tokens for a user before
    issuing a new one (see password_reset_repository.py).

Relationship wiring:
  PasswordResetToken.user  ←back_populates→  User.password_reset_tokens
─────────────────────────────────────────────────────────────────────────────
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Column, DateTime, String, text
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from models.user import User


class PasswordResetToken(SQLModel, table=True):
    __tablename__ = "password_reset_tokens"

    # ── Primary key ───────────────────────────────────────────────────────────
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        nullable=False,
    )

    # ── Foreign key → users ───────────────────────────────────────────────────
    user_id: uuid.UUID = Field(
    sa_column=Column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
)

    # ── Token hash ────────────────────────────────────────────────────────────
    # sha256(raw_token) — 64 hex characters.
    # UNIQUE: each hash must appear at most once across all rows.
    # INDEX: fast lookup by hash on every reset attempt.
    token_hash: str = Field(
        max_length=64,
        unique=True,
        index=True,
        nullable=False,
    )

    # ── Delivery channel ──────────────────────────────────────────────────────
    # "email" → link with token in query param
    # "phone" → 6-digit OTP sent via SMS (hash of the OTP string)
    delivery_method: str = Field(
        default="email",
        max_length=10,
        nullable=False,
    )

    # ── Expiry window ─────────────────────────────────────────────────────────
    # Set by the service layer to utcnow() + 1 hour.
    # We use sa_column because Field() has no timezone-aware DateTime support.
    expires_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )

    # ── Usage flag ────────────────────────────────────────────────────────────
    # None   = not yet consumed (valid for use)
    # non-None = consumed at this timestamp (replay rejected)
    used_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )

    # ── Audit timestamp ───────────────────────────────────────────────────────
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=text("now()"),
            nullable=False,
        )
    )

    # ── Relationship back to User ─────────────────────────────────────────────
    # back_populates="password_reset_tokens" matches User.password_reset_tokens
    user: Optional["User"] = Relationship(back_populates="password_reset_tokens")

    # ── Domain helper ─────────────────────────────────────────────────────────
    def is_valid(self) -> bool:
        """
        True only when both conditions hold:
          1. Token has never been consumed  (used_at is None)
          2. Token has not yet expired      (datetime.now(utc) < expires_at)

        Called by PasswordResetRepository.get_valid() before returning a token.
        """
        if self.used_at is not None:
            return False
        # Make timezone-aware if Postgres returned a naive datetime
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) < expires

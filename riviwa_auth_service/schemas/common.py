"""
schemas/common.py
═══════════════════════════════════════════════════════════════════════════════
Shared primitive types, enums, standalone validators, and generic response
wrappers used by ALL schema modules.

Rules:
  · Import from here — never duplicate these definitions in other files.
  · No circular imports. This file imports NOTHING from the rest of schemas/.
  · config.py constants (e.g. ACCESS_TOKEN_EXPIRE_MINUTES) are referenced
    only in the schemas that need them, not here.
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import re
import uuid
from enum import Enum
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict


# ─────────────────────────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────────────────────────

class OTPChannelEnum(str, Enum):
    """
    Delivery channel for a one-time passcode.

    EMAIL → 6-digit code sent to the user's email address.
    SMS   → 6-digit code sent to the user's phone number via SMS gateway.
    """
    EMAIL = "email"
    SMS   = "sms"


class OTPPurposeEnum(str, Enum):
    """
    Why an OTP is being sent.  Stored server-side on the OTP record so that a
    code issued for REGISTRATION cannot be replayed against PASSWORD_RESET.

    REGISTRATION   → verifying identity during account creation  (TTL 10 min)
    LOGIN          → second factor during login                  (TTL  5 min)
    PASSWORD_RESET → verifying identity before password change   (TTL 10 min)
    PHONE_VERIFY   → standalone phone verification post-register (TTL 10 min)
    EMAIL_VERIFY   → standalone email verification post-register (TTL 10 min)
    """
    REGISTRATION   = "registration"
    LOGIN          = "login"
    PASSWORD_RESET = "password_reset"
    PHONE_VERIFY   = "phone_verify"
    EMAIL_VERIFY   = "email_verify"


# ─────────────────────────────────────────────────────────────────────────────
# Compiled regexes (module-level — compiled once, reused everywhere)
# ─────────────────────────────────────────────────────────────────────────────

# E.164:  +[1-9][7-14 more digits]  →  8–15 total chars
_E164_RE = re.compile(r"^\+[1-9]\d{7,14}$")

# OTP: exactly 6 decimal digits, nothing else.
_OTP_RE = re.compile(r"^\d{6}$")

# Password policy:
#   ≥8 chars · ≥1 uppercase · ≥1 lowercase · ≥1 digit · ≥1 special char
_PASSWORD_RE = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)"
    r"(?=.*[!@#$%^&*()\-_=+\[\]{};:'\",.<>/?\\|`~]).{8,}$"
)

# Username: letters, digits, underscore, hyphen, dot. 3–50 chars.
_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.\-]{3,50}$")


# ─────────────────────────────────────────────────────────────────────────────
# Standalone validator functions  (pure; no side-effects; raise ValueError)
# ─────────────────────────────────────────────────────────────────────────────

def validate_e164(value: str) -> str:
    """
    Strip whitespace, then assert E.164 format.
    Raises ValueError with a human-readable message on failure.
    """
    value = value.strip()
    if not _E164_RE.match(value):
        raise ValueError(
            "Phone number must be in E.164 format — "
            "a leading '+', country code, then subscriber digits. "
            "Example: +12125551234"
        )
    return value


def validate_otp_code(value: str) -> str:
    """Strip whitespace, then assert exactly 6 decimal digits."""
    value = value.strip()
    if not _OTP_RE.match(value):
        raise ValueError("OTP must be exactly 6 digits (0–9 only).")
    return value


def validate_password_strength(value: str) -> str:
    """
    Enforce the platform password policy:
      • Minimum 8 characters
      • At least one uppercase letter  (A–Z)
      • At least one lowercase letter  (a–z)
      • At least one digit             (0–9)
      • At least one special character (!@#$%^&* …)

    Raises ValueError with a full policy description on failure.
    """
    if not _PASSWORD_RE.match(value):
        raise ValueError(
            "Password must be at least 8 characters and include at least one "
            "uppercase letter (A–Z), one lowercase letter (a–z), one digit (0–9), "
            "and one special character (e.g. !@#$%^&*)."
        )
    return value


def validate_username(value: str) -> str:
    """
    Assert username format: 3–50 chars, letters/digits/underscore/dot/hyphen only.
    Raises ValueError on failure.
    """
    value = value.strip()
    if not _USERNAME_RE.match(value):
        raise ValueError(
            "Username must be 3–50 characters and may only contain letters, "
            "digits, underscores (_), hyphens (-), and dots (.)."
        )
    return value


def mask_email(email: str) -> str:
    """
    Return a privacy-safe masked version of an email for API responses.
    alice@example.com  →  al***@example.com
    """
    local, _, domain = email.partition("@")
    visible = local[:2] if len(local) > 2 else local[:1]
    return f"{visible}***@{domain}"


def mask_phone(phone: str) -> str:
    """
    Return a privacy-safe masked version of an E.164 phone number.
    +12125551234  →  +1212***1234
    """
    if len(phone) <= 7:
        return phone[:3] + "***"
    return phone[:4] + "***" + phone[-4:]


# ─────────────────────────────────────────────────────────────────────────────
# Generic response wrappers
# ─────────────────────────────────────────────────────────────────────────────

DataT = TypeVar("DataT")


class MessageResponse(BaseModel):
    """
    Minimal success/info envelope carrying only a human-readable message.

    Used for operations that produce no meaningful data payload:
      · OTP sent
      · Password changed
      · Logout confirmed
      · Account deactivated

    Example JSON:  { "message": "OTP sent to al***@example.com" }
    """
    model_config = ConfigDict(frozen=True)

    message: str


class DataResponse(BaseModel, Generic[DataT]):
    """
    Standard data envelope for responses that carry a typed payload.

    Example JSON:
        {
          "message": "Registration complete.",
          "data": { "user_id": "...", "tokens": { ... } }
        }
    """
    model_config = ConfigDict(frozen=True)

    message: str
    data:    DataT


class PaginatedResponse(BaseModel, Generic[DataT]):
    """
    Standard paginated list envelope.

    Example JSON:
        {
          "items": [...],
          "total": 142,
          "page": 1,
          "page_size": 20,
          "pages": 8
        }
    """
    model_config = ConfigDict(frozen=True)

    items:     list[DataT]
    total:     int
    page:      int
    page_size: int
    pages:     int


class ErrorDetail(BaseModel):
    """
    Single field-level validation error.
    Matches FastAPI's default 422 body shape for easy client parsing.
    """
    model_config = ConfigDict(frozen=True)

    field:   str            # dot-notation field path e.g. "body.email"
    message: str            # human-readable description


class ErrorResponse(BaseModel):
    """
    Standard error envelope returned for 4xx / 5xx responses.

    Example JSON:
        {
          "error": "VALIDATION_ERROR",
          "message": "Request body is invalid.",
          "details": [{ "field": "body.email", "message": "Invalid email." }]
        }
    """
    model_config = ConfigDict(frozen=True)

    error:   str                          # machine-readable error code (SCREAMING_SNAKE)
    message: str                          # human-readable summary
    details: Optional[list[ErrorDetail]] = None   # per-field breakdown (422 only)

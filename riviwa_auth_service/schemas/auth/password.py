"""
schemas/auth/password.py
═══════════════════════════════════════════════════════════════════════════════
Schemas for password management:

  A. FORGOT PASSWORD / RESET  (3 steps, unauthenticated)
  B. CHANGE PASSWORD           (1 step, authenticated)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FLOW A — FORGOT PASSWORD  (3 steps, no auth required)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ┌────────────────────────────────────────────────────────────────────────┐
  │  STEP 1   POST /api/v1/auth/password/forgot                           │
  │           Body : PasswordResetInitRequest                             │
  │             identifier → email OR E.164 phone                        │
  │           Server:                                                      │
  │             · Resolve User by email or phone.                         │
  │             · ALWAYS return HTTP 200 (prevent account enumeration).  │
  │               If no account found: silently no-op.                   │
  │             · If account found AND status=ACTIVE:                    │
  │                 - Invalidate all existing PasswordResetToken rows     │
  │                   for this user (set used_at = now()).                │
  │                 - Generate 6-digit OTP + sha256 token.               │
  │                 - Store in Redis:                                     │
  │                     key = "pwd_reset:<reset_token>"                   │
  │                     val = { user_id, otp_hash, otp_verified: false } │
  │                     TTL = 600 s (10 min)                              │
  │                 - Send OTP → email or SMS based on identifier type.  │
  │           Response : PasswordResetInitResponse                        │
  │             reset_token     (opaque Redis key)                        │
  │             otp_channel / otp_destination (masked)                   │
  └────────────────────────────────────────────────────────────────────────┘
            ↓  user submits OTP
  ┌────────────────────────────────────────────────────────────────────────┐
  │  STEP 2   POST /api/v1/auth/password/forgot/verify-otp                │
  │           Body : PasswordResetOTPVerifyRequest                        │
  │             reset_token + otp_code                                    │
  │           Server:                                                      │
  │             · Validate sha256(otp_code) against stored otp_hash.      │
  │             · On match: set otp_verified=true in Redis.               │
  │           Response : PasswordResetOTPVerifyResponse                   │
  │             reset_token (promoted)                                    │
  └────────────────────────────────────────────────────────────────────────┘
            ↓  user enters new password
  ┌────────────────────────────────────────────────────────────────────────┐
  │  STEP 3   POST /api/v1/auth/password/forgot/reset                     │
  │           Body : PasswordResetCompleteRequest                         │
  │             reset_token + password + confirm_password                 │
  │           Server:                                                      │
  │             · Fetch Redis record; assert otp_verified=true.           │
  │             · Argon2id-hash new password; write to User.              │
  │             · Set used_at on any existing PasswordResetToken rows.   │
  │             · Revoke ALL existing refresh tokens for this user        │
  │               (invalidate every active session — security best practice).│
  │             · Delete Redis key.                                       │
  │           Response : MessageResponse                                  │
  │             "Password reset successfully. Please log in."            │
  └────────────────────────────────────────────────────────────────────────┘

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FLOW B — CHANGE PASSWORD  (1 step, requires Bearer token)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  POST /api/v1/auth/password/change
  Body  : ChangePasswordRequest
    current_password + new_password + confirm_new_password
  Server:
    · Verify current_password against User.hashed_password (Argon2id).
    · Hash new_password; update User.hashed_password.
    · Revoke all other refresh tokens for this user (all devices log out).
    · The CURRENT access token remains valid until its natural expiry.
  Response: MessageResponse  "Password changed."
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from schemas.common import (
    OTPChannelEnum,
    validate_e164,
    validate_otp_code,
    validate_password_strength,
)


# ─────────────────────────────────────────────────────────────────────────────
# FLOW A · Step 1 — Initiate password reset
# ─────────────────────────────────────────────────────────────────────────────

class PasswordResetInitRequest(BaseModel):
    """
    Begin the forgotten-password flow.

    Supply the email address OR phone number associated with the account.
    The server always returns HTTP 200 regardless of whether an account was
    found — this prevents account enumeration (an attacker cannot determine
    which emails/phones are registered by observing different responses).

    If no account is found, the server silently no-ops.
    If an account is found with status=ACTIVE, an OTP is dispatched.
    Accounts with status SUSPENDED/BANNED/DEACTIVATED do not receive OTPs.
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    identifier: str = Field(
        description="Registered email address or E.164 phone number.",
        examples=["alice@example.com", "+12125551234"],
        min_length=5,
        max_length=255,
    )

    # Client context — forwarded to fraud layer
    device_fingerprint: Optional[str] = Field(
        default=None,
        max_length=512,
        description="Optional device fingerprint for fraud scoring.",
    )


class PasswordResetInitResponse(BaseModel):
    """
    Always returned for a valid request (even if no account was found).

    If no account was found, `reset_token` is a dummy value and the OTP
    was never sent.  The client should not be able to distinguish this case
    — display the same "If an account exists, a code was sent" message.
    """
    model_config = ConfigDict(frozen=True)

    reset_token:        str = Field(
        description="Opaque session key. Pass to /password/forgot/verify-otp.",
    )
    otp_channel:        str = Field(description="'email' or 'sms'.")
    otp_destination:    str = Field(description="Masked destination.")
    expires_in_seconds: int = Field(
        default=600,
        description="Seconds until the reset_token expires (10 min).",
    )
    message: str = Field(
        default="If an account with that identifier exists, a verification code has been sent.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# FLOW A · Step 2 — Verify OTP
# ─────────────────────────────────────────────────────────────────────────────

class PasswordResetOTPVerifyRequest(BaseModel):
    """
    Verify the OTP sent in Step 1.

    On success the reset session is promoted (otp_verified=true).
    On failure after 5 attempts the session is deleted — user must restart.
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    reset_token: str = Field(
        description="Token from PasswordResetInitResponse.",
    )
    otp_code: str = Field(
        min_length=6,
        max_length=6,
        description="6-digit OTP received via email or SMS.",
        examples=["920384"],
    )

    @model_validator(mode="after")
    def _validate_otp(self) -> "PasswordResetOTPVerifyRequest":
        self.otp_code = validate_otp_code(self.otp_code)
        return self


class PasswordResetOTPVerifyResponse(BaseModel):
    """Returned after OTP is verified. Pass the promoted token to Step 3."""
    model_config = ConfigDict(frozen=True)

    reset_token: str = Field(description="Same token, now promoted. Pass to /password/forgot/reset.")
    message:     str = Field(default="OTP verified. You may now set a new password.")


# ─────────────────────────────────────────────────────────────────────────────
# FLOW A · Step 3 — Set new password
# ─────────────────────────────────────────────────────────────────────────────

class PasswordResetCompleteRequest(BaseModel):
    """
    Set a new password after OTP verification.

    Requires the promoted `reset_token` from Step 2 (otp_verified=true).

    On success:
      · User.hashed_password is updated with Argon2id hash.
      · All existing refresh tokens for this user are revoked
        (all active sessions on all devices are terminated).
      · The reset_token is deleted from Redis.
      · The caller must log in fresh using /api/v1/auth/login.

    PASSWORD POLICY
    ──────────────────────────────────────────────────────────────────────────
    · Minimum 8 characters
    · At least 1 uppercase (A–Z)
    · At least 1 lowercase (a–z)
    · At least 1 digit (0–9)
    · At least 1 special character (!@#$%^&*…)
    · Must NOT be the same as the current password (enforced in service layer).
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    reset_token: str = Field(
        description="Promoted token from PasswordResetOTPVerifyResponse.",
    )
    new_password: str = Field(
        min_length=8,
        max_length=128,
        description="New password. Must satisfy the platform policy.",
        examples=["NewP@ssw0rd!"],
    )
    confirm_new_password: str = Field(
        min_length=8,
        max_length=128,
        description="Must match `new_password` exactly.",
    )

    @model_validator(mode="after")
    def _validate_password(self) -> "PasswordResetCompleteRequest":
        validate_password_strength(self.new_password)
        if self.new_password != self.confirm_new_password:
            raise ValueError("'new_password' and 'confirm_new_password' do not match.")
        return self


# ─────────────────────────────────────────────────────────────────────────────
# FLOW B — Change password (authenticated user)
# ─────────────────────────────────────────────────────────────────────────────

class ChangePasswordRequest(BaseModel):
    """
    Change the password for the currently authenticated user.

    Requires: Authorization: Bearer <access_token>

    `current_password` is verified against the stored Argon2id hash before
    the new password is accepted.  This prevents an attacker who has gained
    temporary access to an authenticated session from silently changing the
    password.

    On success:
      · User.hashed_password is updated.
      · ALL other refresh tokens for this user are revoked (all other sessions
        on other devices are terminated). The current session's access token
        remains valid until its natural expiry.
      · The server returns HTTP 200 with a MessageResponse.

    Note: if hashed_password is NULL (social-only account), use
    POST /api/v1/auth/social/set-password instead.
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    current_password: str = Field(
        min_length=1,
        max_length=128,
        description="The user's current password (for verification before change).",
    )
    new_password: str = Field(
        min_length=8,
        max_length=128,
        description="New password. Must satisfy the platform policy.",
        examples=["UpdatedP@ss1!"],
    )
    confirm_new_password: str = Field(
        min_length=8,
        max_length=128,
        description="Must match `new_password` exactly.",
    )

    @model_validator(mode="after")
    def _validate(self) -> "ChangePasswordRequest":
        validate_password_strength(self.new_password)
        if self.new_password != self.confirm_new_password:
            raise ValueError("'new_password' and 'confirm_new_password' do not match.")
        if self.current_password == self.new_password:
            raise ValueError("New password must be different from the current password.")
        return self

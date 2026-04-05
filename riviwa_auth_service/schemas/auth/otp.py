"""
schemas/auth/otp.py
═══════════════════════════════════════════════════════════════════════════════
Schemas for standalone OTP operations that occur OUTSIDE the registration and
login flows — e.g. a user post-registration who wants to verify their phone
number, or re-verify their email after changing it.

The registration OTP (RegisterOTPVerifyRequest) and login OTP
(LoginOTPVerifyRequest) live in their respective modules.  This module covers
the general-purpose OTP endpoints:

  POST /api/v1/auth/otp/send        → trigger an OTP to email or SMS
  POST /api/v1/auth/otp/verify      → verify that OTP

Both require an authenticated user (Authorization: Bearer <access_token>).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TYPICAL USE-CASES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  1. Post-registration phone verification
       User registered with email → now adds a phone number to their profile.
       POST /otp/send    { purpose: "phone_verify",  channel: "sms"   }
       POST /otp/verify  { otp_token: "...", otp_code: "384920" }
       → sets User.phone_verified = True

  2. Re-verify email after email change
       User updates email in profile → must verify new address.
       POST /otp/send    { purpose: "email_verify", channel: "email" }
       POST /otp/verify  { otp_token: "...", otp_code: "193847" }
       → sets User.is_email_verified = True  for new email

  3. 2FA toggle
       User enables 2FA from settings page.
       POST /otp/send    { purpose: "phone_verify",  channel: "sms"   }
       POST /otp/verify  { otp_token: "...", otp_code: "..." }
       → sets User.two_factor_enabled = True

Redis key structure:
    "otp:<otp_token>"  →  {
        user_id:      <uuid>,
        purpose:      <OTPPurposeEnum>,
        otp_hash:     sha256(<raw_code>),
        channel:      <OTPChannelEnum>,
        attempts:     0,
        created_at:   <unix_ts>
    }
    TTL = 600 seconds (10 minutes) for all standalone OTPs.
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from schemas.common import OTPChannelEnum, OTPPurposeEnum, validate_otp_code


# ─────────────────────────────────────────────────────────────────────────────
# Send OTP
# ─────────────────────────────────────────────────────────────────────────────

class OTPSendRequest(BaseModel):
    """
    Request a new OTP for the authenticated user.

    The server determines the destination from the user's profile:
      · channel=EMAIL  → sends to User.email
      · channel=SMS    → sends to User.phone_number (must already be set)

    The `purpose` field is stored in the Redis OTP record so that the OTP
    cannot be used for a different operation than intended.

    Rate limiting: 3 send attempts per user per purpose per 10-minute window.
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    purpose: OTPPurposeEnum = Field(
        description=(
            "The operation this OTP authorises. "
            "Must match the purpose passed to /otp/verify. "
            "Values: phone_verify | email_verify."
        ),
        examples=["phone_verify"],
    )
    channel: OTPChannelEnum = Field(
        description=(
            "Delivery channel. "
            "'email' sends to the user's verified email address. "
            "'sms' sends to the user's registered phone number."
        ),
        examples=["sms"],
    )


class OTPSendResponse(BaseModel):
    """Returned after the OTP has been dispatched."""
    model_config = ConfigDict(frozen=True)

    otp_token:          str            = Field(
        description="Opaque token identifying this OTP session. Pass to /otp/verify.",
    )
    otp_channel:        OTPChannelEnum = Field(description="Channel used.")
    otp_destination:    str            = Field(description="Privacy-masked destination.")
    expires_in_seconds: int            = Field(
        default=600,
        description="Seconds until this OTP expires (10 min).",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Verify OTP
# ─────────────────────────────────────────────────────────────────────────────

class OTPVerifyRequest(BaseModel):
    """
    Verify the 6-digit OTP received via email or SMS.

    The `otp_token` must match the one returned by OTPSendResponse.
    The `purpose` must match the purpose stored in the Redis OTP record —
    mismatched purpose is treated as a failed attempt (prevents cross-purpose
    replay even if a valid code is somehow leaked).

    On success:
      · The Redis OTP record is deleted (single-use).
      · The relevant User flag is updated (e.g. phone_verified = True).

    On failure:
      · The attempt counter is incremented.
      · After 5 consecutive wrong codes the OTP record is deleted and the
        user must request a new OTP from /otp/send.
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    otp_token: str = Field(
        description="Token from OTPSendResponse.otp_token.",
    )
    otp_code: str = Field(
        min_length=6,
        max_length=6,
        description="6-digit OTP received via email or SMS.",
        examples=["384920"],
    )
    purpose: OTPPurposeEnum = Field(
        description="Must match the purpose used when sending the OTP.",
        examples=["phone_verify"],
    )

    @model_validator(mode="after")
    def _validate_otp(self) -> "OTPVerifyRequest":
        self.otp_code = validate_otp_code(self.otp_code)
        return self


class OTPVerifyResponse(BaseModel):
    """Returned after a successful OTP verification."""
    model_config = ConfigDict(frozen=True)

    message:  str            = Field(default="OTP verified successfully.")
    purpose:  OTPPurposeEnum = Field(description="The purpose that was verified.")
    verified: bool           = Field(default=True)

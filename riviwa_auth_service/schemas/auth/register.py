"""
schemas/auth/register.py
═══════════════════════════════════════════════════════════════════════════════
Request / response schemas for user account registration.

Three flows are supported:

  A. EMAIL OR PHONE registration  (3 steps)
  B. SOCIAL / OAUTH registration  (1 step + optional password set)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FLOW A — EMAIL or PHONE  (3 steps)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ┌────────────────────────────────────────────────────────────────────────┐
  │  STEP 1   POST /api/v1/auth/register/init                              │
  │           Body : RegisterInitRequest                                   │
  │             · Provide EITHER email OR phone_number (XOR, not both).   │
  │             · Optionally provide first_name / last_name now.          │
  │           Server:                                                      │
  │             · Normalise email (strip + alias, collapse dots for       │
  │               Gmail) and check email_normalized uniqueness.           │
  │               OR validate E.164 phone and check uniqueness.           │
  │             · Reject immediately if account already exists            │
  │               (return HTTP 409 with generic message — no enumeration).│
  │             · Generate 6-digit OTP; store in Redis:                   │
  │               key   = "reg:<registration_token>"                      │
  │               value = { otp_hash: sha256(otp), purpose: REGISTRATION, │
  │                          otp_verified: false, identity: {...} }        │
  │               TTL   = 600 seconds (10 minutes)                        │
  │             · Dispatch OTP → EMAIL channel if email supplied,         │
  │                              SMS   channel if phone supplied.         │
  │           Response : RegisterInitResponse                             │
  │             registration_token  (opaque Redis key, pass to Steps 2&3) │
  │             otp_channel / otp_destination (masked, for UI display)    │
  └────────────────────────────────────────────────────────────────────────┘
            ↓  user enters 6-digit OTP from email/SMS
  ┌────────────────────────────────────────────────────────────────────────┐
  │  STEP 2   POST /api/v1/auth/register/verify-otp                        │
  │           Body : RegisterOTPVerifyRequest                              │
  │             registration_token  (from Step 1)                         │
  │             otp_code            (6 digits)                            │
  │           Server:                                                      │
  │             · Fetch Redis record for registration_token.              │
  │             · Compare sha256(otp_code) against stored otp_hash.       │
  │             · On match: set otp_verified=true; update Redis (same TTL).│
  │             · On mismatch: increment attempt counter; after 5 wrong   │
  │               attempts delete the Redis key → user must restart.      │
  │           Response : RegisterOTPVerifyResponse                        │
  │             registration_token  (same token, now promoted)            │
  └────────────────────────────────────────────────────────────────────────┘
            ↓  user sets their password
  ┌────────────────────────────────────────────────────────────────────────┐
  │  STEP 3   POST /api/v1/auth/register/complete                          │
  │           Body : RegisterCompleteRequest                              │
  │             registration_token  (promoted token from Step 2)          │
  │             password / confirm_password                               │
  │             username (optional — auto-generated if omitted)           │
  │             first_name / last_name (optional)                         │
  │           Server:                                                      │
  │             · Fetch Redis record; assert otp_verified=true.           │
  │             · Argon2id-hash the password.                             │
  │             · Create User row:                                        │
  │                 status            = ACTIVE                            │
  │                 is_email_verified = true  (if email flow)             │
  │                 phone_verified    = true  (if phone flow)             │
  │                 hashed_password   = argon2id(password)               │
  │             · Delete Redis registration session key.                 │
  │             · Issue JWT access token + refresh token immediately.    │
  │           Response : RegisterCompleteResponse  (wraps TokenResponse)  │
  └────────────────────────────────────────────────────────────────────────┘

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FLOW B — SOCIAL / OAUTH  (Google, Apple, Facebook)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ┌────────────────────────────────────────────────────────────────────────┐
  │  STEP 1   POST /api/v1/auth/social                                     │
  │           Body : SocialAuthRequest                                     │
  │             provider  = "google" | "apple" | "facebook"               │
  │             id_token  = JWT returned by the provider SDK              │
  │           Server:                                                      │
  │             · Verify id_token signature with provider's JWKS.         │
  │             · Extract: email, provider_user_id, name (if present).    │
  │             · If email matches existing account:                      │
  │                 Link provider to account (if not already linked).     │
  │                 Issue tokens → acts as social LOGIN.                  │
  │             · If email is new:                                        │
  │                 Create User:  status=ACTIVE, is_email_verified=true,  │
  │                               oauth_provider/oauth_provider_id set,  │
  │                               hashed_password=NULL.                   │
  │                 Issue tokens → acts as social REGISTRATION.           │
  │             · No OTP required — provider verified identity.           │
  │           Response : RegisterCompleteResponse                         │
  │             is_new_user flag tells client whether to show onboarding. │
  └────────────────────────────────────────────────────────────────────────┘

  ┌─ OPTIONAL ─────────────────────────────────────────────────────────────┐
  │  POST /api/v1/auth/social/set-password                                 │
  │  Body : SocialSetPasswordRequest                                       │
  │  Allows a social user to add a password so they can also log in       │
  │  with email + password. Requires a valid Bearer access token.         │
  │  Response: MessageResponse                                             │
  └────────────────────────────────────────────────────────────────────────┘

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PASSWORD POLICY (enforced in Steps 3 and social/set-password)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  · Minimum 8 characters
  · At least one uppercase letter  (A–Z)
  · At least one lowercase letter  (a–z)
  · At least one digit             (0–9)
  · At least one special character (!@#$%^&*…)
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import uuid
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from schemas.auth.login import TokenResponse
from schemas.common import (
    OTPChannelEnum,
    validate_e164,
    validate_otp_code,
    validate_password_strength,
    validate_username,
)


# ─────────────────────────────────────────────────────────────────────────────
# FLOW A · Step 1 — Identity submission
# ─────────────────────────────────────────────────────────────────────────────

class RegisterInitRequest(BaseModel):
    """
    Kick off registration.

    Supply EXACTLY ONE of `email` or `phone_number`.
    Providing both, or neither, raises a validation error immediately.

    `first_name` and `last_name` are optional here — they can also be
    supplied later in Step 3 (RegisterCompleteRequest). Collecting them
    early allows a more personalised OTP email ("Hi Alice, your code is …").
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    # ── Exactly one identity field required ───────────────────────────────────
    email: Optional[EmailStr] = Field(
        default=None,
        description=(
            "Email address to register with. "
            "Provide this OR phone_number — not both."
        ),
        examples=["alice@example.com"],
    )
    phone_number: Optional[str] = Field(
        default=None,
        description=(
            "E.164 phone number to register with. "
            "Provide this OR email — not both. "
            "Example: +12125551234"
        ),
        examples=["+12125551234"],
    )

    # ── Optional profile — collected early for personalised OTP message ───────
    first_name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="User's first name (optional at this step).",
    )
    last_name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="User's last name (optional at this step).",
    )

    # ── Client context — forwarded to fraud layer ─────────────────────────────
    device_fingerprint: Optional[str] = Field(
        default=None,
        max_length=512,
        description="Optional client-side device fingerprint for fraud scoring.",
    )

    @model_validator(mode="after")
    def _xor_identity(self) -> "RegisterInitRequest":
        """Enforce: exactly one of email or phone_number."""
        has_email = self.email is not None
        has_phone = self.phone_number is not None
        if has_email and has_phone:
            raise ValueError(
                "Provide either 'email' or 'phone_number', not both."
            )
        if not has_email and not has_phone:
            raise ValueError(
                "Provide either 'email' or 'phone_number'."
            )
        if has_phone:
            self.phone_number = validate_e164(self.phone_number)  # type: ignore[arg-type]
        return self


class RegisterInitResponse(BaseModel):
    """
    Returned after Step 1 succeeds.

    `registration_token` is a short-lived opaque key stored in Redis (TTL 10 min).
    It binds Steps 1 → 2 → 3 together without embedding the user's identity in
    any URL or client-readable field.

    The client should:
      · Store `registration_token` in memory only (not localStorage).
      · Display `otp_destination` so the user knows where to look.
      · Proceed to /register/verify-otp.
    """
    model_config = ConfigDict(frozen=True)

    registration_token: str = Field(
        description="Opaque session key. Pass to /register/verify-otp and /register/complete.",
    )
    otp_channel:        OTPChannelEnum = Field(description="Channel used: 'email' or 'sms'.")
    otp_destination:    str            = Field(
        description="Privacy-masked destination shown to the user. e.g. 'al***@example.com'.",
    )
    expires_in_seconds: int            = Field(
        default=600,
        description="Seconds until the registration_token (and OTP) expire. Default: 10 min.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# FLOW A · Step 2 — OTP verification
# ─────────────────────────────────────────────────────────────────────────────

class RegisterOTPVerifyRequest(BaseModel):
    """
    Verify the 6-digit OTP delivered in Step 1.

    On success: the Redis registration session is updated with
    `otp_verified = true`. The same `registration_token` is returned,
    now promoted. The client must immediately proceed to Step 3.

    On failure: the attempt counter is incremented. After 5 consecutive
    wrong codes the registration session is deleted and the user must
    restart from Step 1.
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    registration_token: str = Field(
        description="Token from RegisterInitResponse.",
    )
    otp_code: str = Field(
        min_length=6,
        max_length=6,
        description="6-digit OTP received via email or SMS.",
        examples=["483920"],
    )

    @model_validator(mode="after")
    def _validate_otp(self) -> "RegisterOTPVerifyRequest":
        self.otp_code = validate_otp_code(self.otp_code)
        return self


class RegisterOTPVerifyResponse(BaseModel):
    """
    Returned after OTP is verified.

    The `registration_token` is the same string — its server-side
    record has been promoted (otp_verified=true). Pass it to Step 3.
    """
    model_config = ConfigDict(frozen=True)

    registration_token: str = Field(
        description="Same token, now promoted. Pass to /register/complete.",
    )
    message: str = Field(default="OTP verified. Proceed to complete registration.")


# ─────────────────────────────────────────────────────────────────────────────
# FLOW A · Step 3 — Password + profile completion
# ─────────────────────────────────────────────────────────────────────────────

class RegisterCompleteRequest(BaseModel):
    """
    Complete account creation.

    Requires the promoted `registration_token` from Step 2 (otp_verified=true).
    On success a User row is created and the caller is immediately authenticated
    via the returned TokenResponse — no separate login step required.

    Profile fields collected here are merged with anything submitted in Step 1.
    Step 1 values take precedence; Step 3 fields fill in any blanks.

    PASSWORD POLICY
    ──────────────────────────────────────────────────────────────────────────
    • Minimum 8 characters
    • At least 1 uppercase letter  (A–Z)
    • At least 1 lowercase letter  (a–z)
    • At least 1 digit             (0–9)
    • At least 1 special character (!@#$%^&*…)
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    registration_token: str = Field(
        description="Promoted token from RegisterOTPVerifyResponse.",
    )

    # ── Password ──────────────────────────────────────────────────────────────
    password: str = Field(
        min_length=8,
        max_length=128,
        description="New account password. Must satisfy the platform policy.",
        examples=["MyP@ssw0rd!"],
    )
    confirm_password: str = Field(
        min_length=8,
        max_length=128,
        description="Must be identical to `password`.",
    )

    # ── Optional profile ──────────────────────────────────────────────────────
    username: Optional[str] = Field(
        default=None,
        min_length=3,
        max_length=50,
        description=(
            "Desired username. Letters, digits, underscores, hyphens, dots. "
            "Auto-generated from name or email if omitted."
        ),
        examples=["alice_smith"],
    )
    first_name: Optional[str] = Field(default=None, max_length=100)
    last_name:  Optional[str] = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def _validate_password(self) -> "RegisterCompleteRequest":
        validate_password_strength(self.password)
        if self.password != self.confirm_password:
            raise ValueError("'password' and 'confirm_password' do not match.")
        if self.username is not None:
            self.username = validate_username(self.username)
        return self


class RegisterCompleteResponse(BaseModel):
    """
    Returned after successful account creation.

    `is_new_user` is always True for Flow A.
    It is exposed here (and on SocialAuthResponse) so clients can use a
    single response type and branch on `is_new_user` to decide whether
    to show a welcome / onboarding screen.

    The user is immediately authenticated — store `tokens` and proceed.
    """
    model_config = ConfigDict(frozen=True)

    message:     str          = Field(default="Account created successfully.")
    user_id:     uuid.UUID    = Field(description="The newly created user's UUID.")
    is_new_user: bool         = Field(default=True)
    tokens:      TokenResponse = Field(description="Access + refresh token pair. Store securely.")


# ─────────────────────────────────────────────────────────────────────────────
# FLOW B — Social / OAuth  (Google, Apple, Facebook)
# ─────────────────────────────────────────────────────────────────────────────

class SocialAuthRequest(BaseModel):
    """
    Authenticate via a third-party OAuth provider.

    This endpoint handles BOTH social registration and social login in a single
    call — the server determines which applies based on whether the email from
    the provider is already in the database.

    HOW IT WORKS
    ──────────────────────────────────────────────────────────────────────────
    1. The frontend authenticates with the provider (Google Sign-In SDK,
       Sign in with Apple SDK, etc.) and receives an `id_token` (OIDC JWT).
    2. The frontend posts `provider` + `id_token` to this endpoint.
    3. The server verifies the `id_token` signature against the provider's
       published JWKS endpoint and extracts:
         · email          (always present for Google/Facebook)
         · sub            (provider-specific user identifier)
         · name / picture (optional, provider-dependent)
    4. If the email matches an existing User:
         · If oauth_provider is NULL on that User: link the provider account.
         · Issue tokens → caller is logged in.
         · is_new_user = False.
    5. If the email is new:
         · Create User: status=ACTIVE, is_email_verified=True,
           oauth_provider=<provider>, oauth_provider_id=<sub>,
           hashed_password=NULL.
         · Issue tokens.
         · is_new_user = True.

    No OTP step is required — the provider has already verified the user's
    identity. hashed_password is NULL; the user can optionally add a password
    later via POST /api/v1/auth/social/set-password.

    PROVIDER NOTES
    ──────────────────────────────────────────────────────────────────────────
    google   · id_token from google.accounts.id.initialize() callback.
             · Verify via https://oauth2.googleapis.com/tokeninfo or JWKS.
    apple    · identityToken from ASAuthorizationAppleIDCredential.
             · Email may be hidden on second+ sign-in; store on first use.
    facebook · access_token from FB.login() response.
             · Exchange via graph.facebook.com/me?fields=id,email,name.
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    provider: Literal["google", "apple", "facebook"] = Field(
        description="OAuth provider.",
        examples=["google"],
    )
    id_token: str = Field(
        description=(
            "ID token (OIDC JWT) from the provider SDK. "
            "For Google: the 'credential' value from the Sign-In callback. "
            "For Apple: 'identityToken' from ASAuthorizationAppleIDCredential. "
            "For Facebook: the access_token from FB.login()."
        ),
    )
    device_fingerprint: Optional[str] = Field(
        default=None,
        max_length=512,
        description="Optional device fingerprint for fraud scoring.",
    )


class SocialAuthResponse(BaseModel):
    """
    Returned after a successful social authentication (registration or login).

    Use `is_new_user` to decide whether to show a welcome / onboarding screen.
    Use `has_password` to decide whether to prompt the user to set a password
    (recommended for accounts that may also want email+password login).
    """
    model_config = ConfigDict(frozen=True)

    message:      str           = Field(default="Social authentication successful.")
    user_id:      uuid.UUID     = Field(description="User's UUID.")
    is_new_user:  bool          = Field(description="True if a new account was created.")
    has_password: bool          = Field(
        description="False if hashed_password is NULL (social-only account). "
                    "Prompt user to set a password for future email+password login.",
    )
    tokens:       TokenResponse = Field(description="Access + refresh token pair.")


class SocialSetPasswordRequest(BaseModel):
    """
    Add a password to a social-only account.

    Allows a user who originally signed up via Google (and therefore has
    hashed_password=NULL) to also log in using email + password in the future.

    Requires:  Authorization: Bearer <access_token>

    The server will reject this if hashed_password is already set — use
    ChangePasswordRequest (schemas/auth/password.py) to change an existing one.
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    password: str = Field(
        min_length=8,
        max_length=128,
        description="Password to set on the account. Must satisfy the policy.",
    )
    confirm_password: str = Field(
        min_length=8,
        max_length=128,
        description="Must match `password` exactly.",
    )

    @model_validator(mode="after")
    def _validate(self) -> "SocialSetPasswordRequest":
        validate_password_strength(self.password)
        if self.password != self.confirm_password:
            raise ValueError("'password' and 'confirm_password' do not match.")
        return self


# ─────────────────────────────────────────────────────────────────────────────
# OTP resend (shared between registration and login flows)
# ─────────────────────────────────────────────────────────────────────────────

class OTPResendRequest(BaseModel):
    """
    Resend an OTP for an in-progress registration or login session.

    Use when the user did not receive the original OTP (email filtered as spam,
    SMS gateway delay, etc.).

    Rate-limited server-side: maximum 3 resends per session token.
    Each resend generates a NEW OTP and invalidates the previous one.
    The session TTL is NOT extended on resend.

    `session_token` accepts either a `registration_token` or a `login_token` —
    the server resolves the purpose from the Redis record.
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    session_token: str = Field(
        description="The registration_token or login_token from the active session.",
    )


class OTPResendResponse(BaseModel):
    """Returned after a successful OTP resend."""
    model_config = ConfigDict(frozen=True)

    message:         str = Field(default="A new OTP has been sent.")
    otp_channel:     str = Field(description="Channel used: 'email' or 'sms'.")
    otp_destination: str = Field(description="Masked destination.")
    resends_remaining: int = Field(description="How many more resends are allowed for this session.")

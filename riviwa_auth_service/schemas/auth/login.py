"""
schemas/auth/login.py
═══════════════════════════════════════════════════════════════════════════════
Request / response schemas for:
  · JWT + refresh token types  (TokenResponse, TokenPayload)
  · Login flow — 2 steps
  · Token refresh
  · Logout (session revocation)
  · Org dashboard switching  (SwitchOrgRequest / SwitchOrgResponse)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LOGIN FLOW  — 2 steps
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ┌────────────────────────────────────────────────────────────────────────┐
  │  STEP 1   POST /api/v1/auth/login                                      │
  │           Body : LoginRequest                                          │
  │             identifier  → email OR E.164 phone                        │
  │             password    → account password                             │
  │           Server:                                                      │
  │             · Normalise identifier; resolve User row.                  │
  │             · Argon2id verify password.                                │
  │             · Check status=ACTIVE; check not locked.                  │
  │             · Generate 6-digit OTP; store sha256(otp) in Redis         │
  │               (key=login:<login_token>, TTL=5 min, purpose=LOGIN).    │
  │             · Send OTP → email if identifier was email,               │
  │                          SMS   if identifier was phone.               │
  │           Response : LoginCredentialsResponse                         │
  │             login_token      (opaque Redis key, TTL 5 min)            │
  │             otp_channel      email | sms                              │
  │             otp_destination  masked destination                       │
  └────────────────────────────────────────────────────────────────────────┘
            ↓  user submits 6-digit OTP
  ┌────────────────────────────────────────────────────────────────────────┐
  │  STEP 2   POST /api/v1/auth/login/verify-otp                          │
  │           Body : LoginOTPVerifyRequest                                 │
  │             login_token  (from Step 1)                                 │
  │             otp_code     (6 digits from email/SMS)                    │
  │           Server:                                                      │
  │             · Fetch Redis record; verify sha256(otp_code).            │
  │             · Issue JWT access token + opaque refresh token.          │
  │             · Reset failed_login_attempts → 0.                        │
  │             · Update last_login_at, last_login_ip.                    │
  │             · Delete Redis login session key.                         │
  │           Response : TokenResponse                                     │
  └────────────────────────────────────────────────────────────────────────┘

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOKEN MANAGEMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  POST /api/v1/auth/token/refresh
    Body  : RefreshTokenRequest
    Server: verify refresh token in Redis → issue new access token
            (refresh token is rotated — old one deleted, new one stored).
    Response: TokenResponse

  POST /api/v1/auth/token/logout
    Body  : LogoutRequest
    Server: add access token JTI to Redis deny-list (TTL = remaining exp).
            Delete refresh token from Redis.
    Response: MessageResponse

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ORG DASHBOARD SWITCHING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  POST /api/v1/auth/switch-org
    Body  : SwitchOrgRequest   org_id = UUID → switch to org dashboard
                               org_id = null → return to personal view
    Server: validate OrganisationMember exists and is ACTIVE.
            UPDATE users SET active_org_id = <org_id>.
            Issue new token pair scoped to the new context.
    Response: SwitchOrgResponse

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
JWT PAYLOAD STRUCTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  {
    "sub":           "user-uuid",       ← users.id
    "jti":           "token-uuid",      ← for deny-list revocation
    "iat":           1700000000,        ← issued-at  (Unix timestamp)
    "exp":           1700001800,        ← iat + ACCESS_TOKEN_EXPIRE_MINUTES×60
    "org_id":        "org-uuid"|null,   ← active dashboard context
    "org_role":      "owner"|null,      ← role in active org
    "platform_role": "admin"|null       ← super_admin/admin/moderator or null
  }

  ACCESS_TOKEN_EXPIRE_MINUTES is read from core/config.py → settings.
  Default: 30 min.  expires_in = 30 × 60 = 1800 seconds.
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from schemas.common import validate_otp_code


# ─────────────────────────────────────────────────────────────────────────────
# Token types  (defined first — imported by register.py to avoid circular deps)
# ─────────────────────────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    """
    JWT access token + opaque refresh token pair.

    Returned after:
      · Successful OTP verification at /login/verify-otp
      · Successful registration at /register/complete
      · Social registration / login at /auth/social
      · Token refresh at /token/refresh
      · Org dashboard switch at /switch-org

    access_token   Short-lived signed JWT (HS256, alg from settings.ALGORITHM).
                   TTL = settings.ACCESS_TOKEN_EXPIRE_MINUTES minutes.
                   Include in every authenticated request:
                     Authorization: Bearer <access_token>

    refresh_token  Long-lived opaque token (UUID stored in Redis).
                   Default TTL = 7 days.
                   Only used at POST /api/v1/auth/token/refresh.
                   Rotated on every refresh — old token deleted immediately.

    token_type     Always "bearer".

    expires_in     Access token lifetime in seconds.
                   = settings.ACCESS_TOKEN_EXPIRE_MINUTES × 60
                   Clients should proactively refresh when this approaches 0.
    """
    model_config = ConfigDict(frozen=True)

    access_token:  str = Field(description="Short-lived signed JWT.")
    refresh_token: str = Field(description="Long-lived opaque refresh token (Redis-backed).")
    token_type:    str = Field(default="bearer", description="Always 'bearer'.")
    expires_in:    int = Field(
        description=(
            "Access token lifetime in seconds. "
            "= settings.ACCESS_TOKEN_EXPIRE_MINUTES × 60  (default 1800)."
        ),
    )


class TokenPayload(BaseModel):
    """
    Decoded and validated JWT payload.

    Used internally by FastAPI auth dependencies (Bearer token middleware).
    Never serialised and returned to a client.

    Fields mirror the JWT claims described in the module docstring.
    The `jti` (JWT ID) is stored in the Redis deny-list when the token is
    revoked (logout or token rotation).
    """
    model_config = ConfigDict(frozen=True)

    sub:           uuid.UUID            # users.id
    jti:           uuid.UUID            # deny-list key
    iat:           int                  # issued-at  (Unix timestamp)
    exp:           int                  # expiry     (Unix timestamp)
    org_id:        Optional[uuid.UUID] = None   # null → personal view
    org_role:      Optional[str]       = None   # owner/admin/manager/member
    platform_role: Optional[str]       = None   # super_admin/admin/moderator


# ─────────────────────────────────────────────────────────────────────────────
# Step 1 — Credentials
# ─────────────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    """
    Submit identifier + password to initiate a login session.

    `identifier` accepts either:
      · Email address  — alice@example.com
      · E.164 phone    — +12125551234

    The service layer detects which format was submitted, normalises the email
    (strips + aliases, dots for Gmail) or strips the phone, then resolves the
    User row.  A single generic error is returned whether the identifier is
    unknown or the password is wrong (timing-safe; avoids user enumeration).

    On success an OTP is dispatched and a short-lived `login_token` returned.
    The client must NOT store `login_token` beyond the current session flow.
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    identifier: str = Field(
        description="Registered email address or E.164 phone number.",
        examples=["alice@example.com", "+12125551234"],
        min_length=5,
        max_length=255,
    )
    password: str = Field(
        description="Account password.",
        min_length=1,
        max_length=128,
    )

    # Client context — forwarded to fraud-scoring layer
    device_fingerprint: Optional[str] = Field(
        default=None,
        max_length=512,
        description=(
            "Optional client-side device fingerprint string. "
            "Used by the fraud-detection layer for velocity checks. "
            "Send if available; omit if not."
        ),
    )


class LoginCredentialsResponse(BaseModel):
    """
    Returned after credentials are verified in Step 1.

    An OTP has been dispatched to `otp_destination`.
    The client must present `login_token` + the OTP at /login/verify-otp.

    `login_token` is an opaque key stored in Redis (TTL 5 min).
    It is single-use — consumed and deleted on successful OTP verification.
    """
    model_config = ConfigDict(frozen=True)

    login_token:        str          = Field(description="Opaque session key. Submit to /login/verify-otp.")
    otp_channel:        str          = Field(description="Delivery channel: 'email' or 'sms'.")
    otp_destination:    str          = Field(description="Privacy-masked destination e.g. 'al***@example.com'.")
    expires_in_seconds: int          = Field(default=300, description="Seconds until login_token expires (default 5 min).")


# ─────────────────────────────────────────────────────────────────────────────
# Step 2 — OTP verification → token issuance
# ─────────────────────────────────────────────────────────────────────────────

class LoginOTPVerifyRequest(BaseModel):
    """
    Verify the 6-digit OTP and receive the JWT token pair.

    On success:
      · The login session key is deleted from Redis (single-use).
      · failed_login_attempts is reset to 0 on the User row.
      · last_login_at / last_login_ip are updated.
      · A TokenResponse is issued immediately.

    On failure:
      · failed_login_attempts is incremented.
      · After settings.MAX_LOGIN_ATTEMPTS (recommended: 5) failures the
        User row is locked for settings.LOCKOUT_DURATION_MINUTES minutes.
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    login_token: str = Field(
        description="Token returned by /login (LoginCredentialsResponse.login_token).",
    )
    otp_code: str = Field(
        min_length=6,
        max_length=6,
        description="6-digit OTP received via email or SMS.",
        examples=["193847"],
    )

    @model_validator(mode="after")
    def _validate_otp(self) -> "LoginOTPVerifyRequest":
        self.otp_code = validate_otp_code(self.otp_code)
        return self


# ─────────────────────────────────────────────────────────────────────────────
# Token management — refresh + logout
# ─────────────────────────────────────────────────────────────────────────────

class RefreshTokenRequest(BaseModel):
    """
    Exchange a valid refresh token for a new access token.

    The refresh token is rotated on every call:
      · The submitted refresh token is deleted from Redis.
      · A new refresh token is stored with a fresh TTL.
      · A new access token is issued.

    Clients should call this endpoint proactively (e.g. when
    TokenResponse.expires_in drops below 60 seconds) rather than after
    receiving a 401, to maintain a seamless user experience.
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    refresh_token: str = Field(
        description="Long-lived opaque refresh token from the last TokenResponse.",
    )


class LogoutRequest(BaseModel):
    """
    Terminate the current authenticated session.

    The server performs two atomic operations:
      1. Adds the current access token's JTI to the Redis deny-list
         with TTL = remaining seconds until access token expiry.
         This immediately invalidates the access token even before it expires.
      2. Deletes the refresh token from Redis, preventing future refreshes.

    After logout:
      · Any request using the old access token will receive HTTP 401.
      · The refresh token cannot be used to obtain new tokens.
      · The User row is unaffected (account remains active).
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    refresh_token: str = Field(
        description="The refresh token to revoke. From the last TokenResponse.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Org dashboard switching
# ─────────────────────────────────────────────────────────────────────────────

class SwitchOrgRequest(BaseModel):
    """
    Switch the active dashboard context for the authenticated user.

    org_id = <UUID>  → switch to that org's dashboard.
                       The service validates an ACTIVE OrganisationMember
                       row exists for (current_user.id, org_id).
                       The org must have status=ACTIVE.
    org_id = null    → return to the personal / consumer view.

    On success:
      · UPDATE users SET active_org_id = <org_id>
      · A new token pair is issued with the updated org_id + org_role claims.
      · The old access token JTI is added to the deny-list.
      · The old refresh token is revoked.
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    org_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Target organisation UUID, or null to return to personal view.",
    )


class SwitchOrgResponse(BaseModel):
    """
    Returned after a successful dashboard context switch.
    The new token pair carries the updated org_id and org_role JWT claims.
    Clients should replace their stored token pair with these values.
    """
    model_config = ConfigDict(frozen=True)

    message:  str             = Field(default="Dashboard context switched.")
    tokens:   TokenResponse   = Field(description="New token pair; replace stored tokens immediately.")
    org_id:   Optional[uuid.UUID] = Field(default=None, description="Active org UUID, or null for personal view.")
    org_role: Optional[str]       = Field(default=None, description="Role in the active org, or null.")

# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  riviwa_auth_service  |  Port: 8000  |  DB: auth_db (5433)
# FILE     :  schemas/__init__.py
# ───────────────────────────────────────────────────────────────────────────
"""
schemas/__init__.py
═══════════════════════════════════════════════════════════════════════════════
Public re-export surface for all Pydantic v2 request + response schemas.

Package layout
──────────────
  schemas/
    __init__.py              ← this file (re-exports everything)
    common.py                ← enums · validators · generic envelopes
    user.py                  ← user read / update schemas
    auth/
      __init__.py
      login.py               ← TokenResponse · TokenPayload · LoginRequest …
      register.py            ← RegisterInitRequest … SocialAuthRequest …
      otp.py                 ← standalone OTP send / verify (post-auth)
      password.py            ← forgot-password flow · change-password

Import pattern in routers — always import from the package root:

    from app.schemas import (
        RegisterInitRequest,
        RegisterInitResponse,
        RegisterOTPVerifyRequest,
        RegisterOTPVerifyResponse,
        RegisterCompleteRequest,
        RegisterCompleteResponse,
        SocialAuthRequest,
        SocialAuthResponse,
        SocialSetPasswordRequest,
        OTPResendRequest,
        OTPResendResponse,
        LoginRequest,
        LoginCredentialsResponse,
        LoginOTPVerifyRequest,
        TokenResponse,
        TokenPayload,
        RefreshTokenRequest,
        LogoutRequest,
        SwitchOrgRequest,
        SwitchOrgResponse,
        OTPSendRequest,
        OTPSendResponse,
        OTPVerifyRequest,
        OTPVerifyResponse,
        PasswordResetInitRequest,
        PasswordResetInitResponse,
        PasswordResetOTPVerifyRequest,
        PasswordResetOTPVerifyResponse,
        PasswordResetCompleteRequest,
        ChangePasswordRequest,
        UserPublicResponse,
        UserPrivateResponse,
        UserUpdateRequest,
        UserAvatarUpdateRequest,
        MessageResponse,
        ErrorResponse,
        ErrorDetail,
        DataResponse,
        PaginatedResponse,
        OTPChannelEnum,
        OTPPurposeEnum,
    )

Auth flow endpoint → schema mapping reference
──────────────────────────────────────────────
  REGISTRATION (email / phone)
    POST /auth/register/init             RegisterInitRequest       → RegisterInitResponse
    POST /auth/register/verify-otp       RegisterOTPVerifyRequest  → RegisterOTPVerifyResponse
    POST /auth/register/complete         RegisterCompleteRequest   → RegisterCompleteResponse
    POST /auth/register/resend-otp       OTPResendRequest          → OTPResendResponse

  REGISTRATION (social / OAuth)
    POST /auth/social                    SocialAuthRequest         → SocialAuthResponse
    POST /auth/social/set-password       SocialSetPasswordRequest  → MessageResponse

  LOGIN
    POST /auth/login                     LoginRequest              → LoginCredentialsResponse
    POST /auth/login/verify-otp          LoginOTPVerifyRequest     → TokenResponse
    POST /auth/login/resend-otp          OTPResendRequest          → OTPResendResponse

  TOKEN MANAGEMENT
    POST /auth/token/refresh             RefreshTokenRequest       → TokenResponse
    POST /auth/token/logout              LogoutRequest             → MessageResponse

  ORG DASHBOARD SWITCH
    POST /auth/switch-org                SwitchOrgRequest          → SwitchOrgResponse

  STANDALONE OTP  (authenticated — phone/email verify, 2FA setup)
    POST /auth/otp/send                  OTPSendRequest            → OTPSendResponse
    POST /auth/otp/verify                OTPVerifyRequest          → OTPVerifyResponse

  PASSWORD RESET  (unauthenticated)
    POST /auth/password/forgot           PasswordResetInitRequest  → PasswordResetInitResponse
    POST /auth/password/forgot/verify-otp PasswordResetOTPVerifyRequest → PasswordResetOTPVerifyResponse
    POST /auth/password/forgot/reset     PasswordResetCompleteRequest  → MessageResponse

  CHANGE PASSWORD  (authenticated)
    POST /auth/password/change           ChangePasswordRequest     → MessageResponse

  USER PROFILE
    GET  /users/me                       —                         → UserPrivateResponse
    PATCH /users/me                      UserUpdateRequest         → UserPrivateResponse
    POST /users/me/avatar                UserAvatarUpdateRequest   → UserPrivateResponse

Config constants consumed by schemas / services
───────────────────────────────────────────────
  settings.ACCESS_TOKEN_EXPIRE_MINUTES   JWT access token lifetime
  settings.REFRESH_TOKEN_EXPIRE_DAYS     Refresh token lifetime
  settings.ALGORITHM                     JWT algorithm (HS256)
  settings.SECRET_KEY                    JWT signing secret
  settings.OTP_REGISTRATION_TTL_SECONDS  Registration OTP session lifetime (600 s)
  settings.OTP_LOGIN_TTL_SECONDS         Login OTP session lifetime         (300 s)
  settings.OTP_PASSWORD_RESET_TTL_SECONDS Password reset OTP lifetime       (600 s)
  settings.OTP_STANDALONE_TTL_SECONDS    Standalone OTP lifetime            (600 s)
  settings.OTP_MAX_ATTEMPTS              Wrong codes before session deleted  (5)
  settings.OTP_RESEND_LIMIT              Max resends per session             (3)
  settings.OTP_LENGTH                    OTP digit count                     (6)
  settings.MAX_LOGIN_ATTEMPTS            Failed password attempts → lockout  (5)
  settings.LOCKOUT_DURATION_MINUTES      Account lockout duration            (30 min)
  settings.GOOGLE_CLIENT_ID              Google id_token audience verify
  settings.APPLE_CLIENT_ID              Apple identity_token audience verify
  settings.FACEBOOK_APP_ID/SECRET        Facebook access_token verify
═══════════════════════════════════════════════════════════════════════════════
"""

# ── Common primitives ─────────────────────────────────────────────────────────
from schemas.common import (
    OTPChannelEnum,
    OTPPurposeEnum,
    MessageResponse,
    DataResponse,
    PaginatedResponse,
    ErrorDetail,
    ErrorResponse,
    mask_email,
    mask_phone,
    validate_e164,
    validate_otp_code,
    validate_password_strength,
    validate_username,
)

# ── Auth — Login + Token types ────────────────────────────────────────────────
from schemas.auth.login import (
    TokenResponse,
    TokenPayload,
    LoginRequest,
    LoginCredentialsResponse,
    LoginOTPVerifyRequest,
    RefreshTokenRequest,
    LogoutRequest,
    SwitchOrgRequest,
    SwitchOrgResponse,
)

# ── Auth — Registration ───────────────────────────────────────────────────────
from schemas.auth.register import (
    RegisterInitRequest,
    RegisterInitResponse,
    RegisterOTPVerifyRequest,
    RegisterOTPVerifyResponse,
    RegisterCompleteRequest,
    RegisterCompleteResponse,
    SocialAuthRequest,
    SocialAuthResponse,
    SocialSetPasswordRequest,
    OTPResendRequest,
    OTPResendResponse,
)

# ── Auth — Standalone OTP (authenticated) ────────────────────────────────────
from schemas.auth.otp import (
    OTPSendRequest,
    OTPSendResponse,
    OTPVerifyRequest,
    OTPVerifyResponse,
)

# ── Auth — Password management ────────────────────────────────────────────────
from schemas.auth.password import (
    PasswordResetInitRequest,
    PasswordResetInitResponse,
    PasswordResetOTPVerifyRequest,
    PasswordResetOTPVerifyResponse,
    PasswordResetCompleteRequest,
    ChangePasswordRequest,
)

# ── User ──────────────────────────────────────────────────────────────────────
from schemas.user import (
    UserPublicResponse,
    UserPrivateResponse,
    UserUpdateRequest,
    UserAvatarUpdateRequest,
)

# ── Organisation ──────────────────────────────────────────────────────────────
from schemas.organisation import (
    OrgResponse,
    OrgListResponse,
    MemberResponse,
    InviteResponse,
    CreateOrgRequest,
    UpdateOrgRequest,
    AddMemberRequest,
    ChangeRoleRequest,
    TransferOwnershipRequest,
    SendInviteRequest,
    AdminStatusRequest,
)


__all__ = [
    # ── Enums ─────────────────────────────────────────────────────────────────
    "OTPChannelEnum",
    "OTPPurposeEnum",
    # ── Generic envelopes ─────────────────────────────────────────────────────
    "MessageResponse",
    "DataResponse",
    "PaginatedResponse",
    "ErrorDetail",
    "ErrorResponse",
    # ── Utility functions (re-exported for service-layer use) ─────────────────
    "mask_email",
    "mask_phone",
    "validate_e164",
    "validate_otp_code",
    "validate_password_strength",
    "validate_username",
    # ── Token ─────────────────────────────────────────────────────────────────
    "TokenResponse",
    "TokenPayload",
    # ── Login ─────────────────────────────────────────────────────────────────
    "LoginRequest",
    "LoginCredentialsResponse",
    "LoginOTPVerifyRequest",
    "RefreshTokenRequest",
    "LogoutRequest",
    "SwitchOrgRequest",
    "SwitchOrgResponse",
    # ── Registration (email / phone) ──────────────────────────────────────────
    "RegisterInitRequest",
    "RegisterInitResponse",
    "RegisterOTPVerifyRequest",
    "RegisterOTPVerifyResponse",
    "RegisterCompleteRequest",
    "RegisterCompleteResponse",
    # ── Registration (social / OAuth) ─────────────────────────────────────────
    "SocialAuthRequest",
    "SocialAuthResponse",
    "SocialSetPasswordRequest",
    # ── OTP resend (shared between register + login flows) ────────────────────
    "OTPResendRequest",
    "OTPResendResponse",
    # ── Standalone OTP (authenticated — phone/email verify) ───────────────────
    "OTPSendRequest",
    "OTPSendResponse",
    "OTPVerifyRequest",
    "OTPVerifyResponse",
    # ── Password management ───────────────────────────────────────────────────
    "PasswordResetInitRequest",
    "PasswordResetInitResponse",
    "PasswordResetOTPVerifyRequest",
    "PasswordResetOTPVerifyResponse",
    "PasswordResetCompleteRequest",
    "ChangePasswordRequest",
    # ── User ──────────────────────────────────────────────────────────────────
    "UserPublicResponse",
    "UserPrivateResponse",
    "UserUpdateRequest",
    "UserAvatarUpdateRequest",
    # ── Organisation ──────────────────────────────────────────────────────────
    "OrgResponse",
    "OrgListResponse",
    "MemberResponse",
    "InviteResponse",
    "CreateOrgRequest",
    "UpdateOrgRequest",
    "AddMemberRequest",
    "ChangeRoleRequest",
    "TransferOwnershipRequest",
    "SendInviteRequest",
    "AdminStatusRequest",
]

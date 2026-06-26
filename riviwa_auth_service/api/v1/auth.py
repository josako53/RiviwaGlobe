"""
app/api/v1/auth.py
═══════════════════════════════════════════════════════════════════════════════
Authentication endpoints.

Routes
──────
  POST /api/v1/auth/login                  Step 1 — credentials → OTP dispatch
  POST /api/v1/auth/login/verify-otp       Step 2 — OTP → token pair  [NOW LIVE]
  POST /api/v1/auth/token/refresh          Rotate refresh token
  POST /api/v1/auth/token/logout           Revoke current session
  POST /api/v1/auth/switch-org             Switch active org dashboard
  POST /api/v1/auth/social                 Social (OAuth) login / registration  [NOW LIVE]
  POST /api/v1/auth/social/set-password    Add password to social-only account

Login flow change from original
────────────────────────────────
  login() now returns LoginCredentialsResponse (not TokenResponse) because
  all logins go through the 2-step OTP flow.  The actual tokens are issued
  by verify_login_otp() once the OTP is confirmed.
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import time
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, status

from api.v1.deps import AuthServiceDep, OAuthServiceDep, UserServiceDep
from core.dependencies import (
    TokenClaims,
    get_client_ip,
    get_current_token,
    get_user_agent,
    require_active_user,
)
from models.user import User
from schemas.auth.login import (
    LoginCredentialsResponse,
    LoginOTPVerifyRequest,
    LoginRequest,
    LogoutRequest,
    RefreshTokenRequest,
    SwitchOrgRequest,
    SwitchOrgResponse,
    TokenResponse,
)
from schemas.auth.register import (
    SocialAuthRequest,
    SocialAuthResponse,
    SocialSetPasswordRequest,
)
from schemas.common import MessageResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ─────────────────────────────────────────────────────────────────────────────
# Login — Step 1: credentials → OTP dispatch
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/login",
    response_model=LoginCredentialsResponse,
    status_code=status.HTTP_200_OK,
    summary="Login — Step 1: submit credentials",
    responses={
        400: {"description": "Validation error"},
        401: {"description": "Invalid credentials"},
        403: {"description": "Account suspended / banned / deactivated"},
        423: {"description": "Account temporarily locked"},
    },
)
async def login(
    body:       LoginRequest,
    svc:        AuthServiceDep,
    ip_address: Annotated[str,           Depends(get_client_ip)],
    user_agent: Annotated[Optional[str], Depends(get_user_agent)],
) -> LoginCredentialsResponse:
    """
    Verify identifier (email or E.164 phone) and password.

    On success, a 6-digit OTP is dispatched to the user's email or phone
    and a short-lived `login_token` is returned.

    Pass `login_token` + the received OTP to `POST /auth/login/verify-otp`
    to receive the actual JWT token pair.

    The `login_token` expires after **5 minutes**.
    """
    result = await svc.login(
        identifier=body.identifier,
        password=body.password,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return LoginCredentialsResponse(
        login_token=result["login_token"],
        otp_channel=result["otp_channel"],
        otp_destination=result["otp_destination"],
        expires_in_seconds=result["expires_in_seconds"],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Login — Step 2: OTP verification → token issuance
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/login/verify-otp",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Login — Step 2: verify OTP and receive tokens",
    responses={
        400: {"description": "Invalid or expired OTP"},
        429: {"description": "Maximum OTP attempts exceeded — session destroyed"},
    },
)
async def login_verify_otp(
    body:       LoginOTPVerifyRequest,
    svc:        AuthServiceDep,
    ip_address: Annotated[str, Depends(get_client_ip)],
) -> TokenResponse:
    """
    Verify the 6-digit OTP dispatched in Step 1.

    On success:
    - A JWT access token + opaque refresh token pair is issued.
    - `failed_login_attempts` is reset to 0 on the User row.
    - `last_login_at` and `last_login_ip` are updated.
    - The login session is deleted from Redis (single-use).

    Store `access_token` in memory and `refresh_token` in a secure cookie or
    encrypted storage. Include `access_token` as `Authorization: Bearer <token>`
    on every authenticated request.

    After **5 consecutive wrong codes** the session is destroyed and the user
    must restart from Step 1.
    """
    result = await svc.verify_login_otp(
        login_token=body.login_token,
        otp_code=body.otp_code,
        ip_address=ip_address,
    )
    return TokenResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        token_type=result["token_type"],
        expires_in=result["expires_in"],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Token refresh
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/token/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
    responses={401: {"description": "Refresh token invalid or expired"}},
)
async def refresh_tokens(
    body:       RefreshTokenRequest,
    svc:        AuthServiceDep,
    ip_address: Annotated[str, Depends(get_client_ip)],
) -> TokenResponse:
    """
    Exchange a valid refresh token for a new access token.

    The submitted refresh token is **rotated** on every call — it is deleted
    from Redis and a new one is stored.  Store the new `refresh_token`
    immediately; the old one cannot be used again.
    """
    result = await svc.refresh_tokens(
        refresh_token=body.refresh_token,
        ip_address=ip_address,
    )
    return TokenResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        token_type=result["token_type"],
        expires_in=result["expires_in"],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Logout
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/token/logout",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Logout — revoke session",
    responses={401: {"description": "Not authenticated"}},
)
async def logout(
    body:   LogoutRequest,
    svc:    AuthServiceDep,
    token:  Annotated[TokenClaims, Depends(get_current_token)],
) -> MessageResponse:
    """
    Terminate the current session.

    Adds the current JWT's JTI to the Redis deny-list and deletes the
    refresh token. Subsequent requests using the old access token receive
    HTTP 401 immediately, even before the token would naturally expire.
    """
    now = int(time.time())
    remaining_seconds = max(token.exp - now, 0)

    await svc.logout(
        user_id=token.sub,
        jti=str(token.jti),
        refresh_token=body.refresh_token,
        access_token_remaining_seconds=remaining_seconds,
    )
    return MessageResponse(message="Logged out successfully.")


# ─────────────────────────────────────────────────────────────────────────────
# Switch org dashboard
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/switch-org",
    response_model=SwitchOrgResponse,
    status_code=status.HTTP_200_OK,
    summary="Switch active org dashboard",
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not an active member of the requested org"},
    },
)
async def switch_org(
    body: SwitchOrgRequest,
    svc:  AuthServiceDep,
    user: Annotated[User, Depends(require_active_user)],
) -> SwitchOrgResponse:
    """
    Switch the active dashboard context.

    - `org_id = <UUID>` → switch to that organisation's dashboard.
      The caller must be an **active member** of the org.
    - `org_id = null` → return to the personal / consumer view.

    Returns a **new token pair** scoped to the new context.
    Replace your stored tokens immediately.
    """
    result = await svc.switch_org(user=user, org_id=body.org_id)
    tokens = TokenResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        token_type=result["token_type"],
        expires_in=result["expires_in"],
    )
    return SwitchOrgResponse(
        tokens=tokens,
        org_id=result.get("org_id"),
        org_role=result.get("org_role"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Social / OAuth login + registration
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/social",
    response_model=SocialAuthResponse,
    status_code=status.HTTP_200_OK,
    summary="Social login / registration (Google · Apple · Facebook)",
    responses={
        401: {"description": "Invalid or expired provider token"},
        409: {"description": "Email linked to a different OAuth provider"},
    },
)
async def social_auth(
    body:       SocialAuthRequest,
    svc:        OAuthServiceDep,
    ip_address: Annotated[str,           Depends(get_client_ip)],
    user_agent: Annotated[Optional[str], Depends(get_user_agent)],
) -> SocialAuthResponse:
    """
    Authenticate via Google, Apple, or Facebook.

    Handles both social **registration** and social **login** in a single call.
    The server determines which applies based on whether the email from the
    provider already exists in the database.

    `is_new_user` in the response tells the client whether to show the
    onboarding flow.

    `has_password` indicates whether this account has a password set.
    If `False`, prompt the user to optionally add a password via
    `POST /auth/social/set-password` (allows future email+password login).

    **Google:** pass the `credential` value from the Sign-In callback.
    **Apple:** pass `identityToken` from `ASAuthorizationAppleIDCredential`.
    **Facebook:** pass the `accessToken` from `FB.login()`.
    """
    result = await svc.authenticate(
        provider=body.provider,
        id_token=body.id_token,
        ip_address=ip_address,
        device_fingerprint=body.device_fingerprint,
    )
    tokens = TokenResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        token_type=result["token_type"],
        expires_in=result["expires_in"],
    )
    return SocialAuthResponse(
        user_id=result["user_id"],
        is_new_user=result["is_new_user"],
        has_password=result["has_password"],
        tokens=tokens,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Social — set password on OAuth-only account
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/social/set-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Set a password on a social-only account",
    responses={
        400: {"description": "Password does not meet policy"},
        401: {"description": "Not authenticated"},
        409: {"description": "Account already has a password — use /password/change"},
    },
)
async def social_set_password(
    body: SocialSetPasswordRequest,
    svc:  UserServiceDep,
    user: Annotated[User, Depends(require_active_user)],
) -> MessageResponse:
    """
    Allow a social-only account (OAuth, no password) to add a password.

    After this call the user can log in with both their social provider
    **and** email + password.

    Returns HTTP 409 if a password is already set — use
    `POST /auth/password/change` to change an existing password.
    """
    await svc.set_password_for_oauth_user(user=user, new_pass=body.password)
    return MessageResponse(
        message="Password set. You can now log in with email and password."
    )

"""
app/api/v1/password.py
═══════════════════════════════════════════════════════════════════════════════
Password management endpoints.

Routes
──────
  POST /api/v1/auth/password/forgot              Step 1 — initiate reset (send OTP)  [NOW LIVE]
  POST /api/v1/auth/password/forgot/verify-otp   Step 2 — verify OTP                 [NOW LIVE]
  POST /api/v1/auth/password/forgot/reset        Step 3 — set new password            [NOW LIVE]
  POST /api/v1/auth/password/change              Change password (authenticated)

All three forgot-password steps now call UserService methods backed by a
Redis OTP session (pwd_reset:<token>, TTL 10 min).
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from api.v1.deps import UserServiceDep
from core.dependencies import get_client_ip, require_active_user, require_active_user_or_channel
from models.user import User
from schemas.auth.password import (
    ChangePasswordRequest,
    PasswordResetCompleteRequest,
    PasswordResetInitRequest,
    PasswordResetInitResponse,
    PasswordResetOTPVerifyRequest,
    PasswordResetOTPVerifyResponse,
)
from schemas.common import MessageResponse

router = APIRouter(prefix="/auth/password", tags=["Password"])


# ─────────────────────────────────────────────────────────────────────────────
# Forgot password — Step 1: initiate
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/forgot",
    response_model=PasswordResetInitResponse,
    status_code=status.HTTP_200_OK,
    summary="Forgot password — Step 1: request OTP",
)
async def forgot_password_init(
    body:       PasswordResetInitRequest,
    svc:        UserServiceDep,
    ip_address: Annotated[str, Depends(get_client_ip)],
) -> PasswordResetInitResponse:
    """
    Begin the forgot-password flow.

    Supply the `identifier` (email address or E.164 phone number).

    The server **always returns HTTP 200** regardless of whether an account
    was found — this prevents account enumeration. If no active account
    matches, the operation is silently ignored.

    If an account is found:
    - All existing password reset tokens are invalidated.
    - A 6-digit OTP is generated and dispatched via email or SMS.
    - A `reset_token` is returned (Redis-backed, TTL 10 minutes).

    Pass `reset_token` to `/password/forgot/verify-otp`.
    """
    result = await svc.initiate_password_reset(
        identifier=body.identifier,
        ip_address=ip_address,
    )
    return PasswordResetInitResponse(
        reset_token=result["reset_token"],
        otp_channel=result["otp_channel"],
        otp_destination=result["otp_destination"],
        expires_in_seconds=result["expires_in_seconds"],
        message=result["message"],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Forgot password — Step 2: verify OTP
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/forgot/verify-otp",
    response_model=PasswordResetOTPVerifyResponse,
    status_code=status.HTTP_200_OK,
    summary="Forgot password — Step 2: verify OTP",
    responses={
        400: {"description": "Invalid OTP"},
        410: {"description": "Reset session expired — restart from Step 1"},
        429: {"description": "Maximum OTP attempts exceeded"},
    },
)
async def forgot_password_verify_otp(
    body: PasswordResetOTPVerifyRequest,
    svc:  UserServiceDep,
) -> PasswordResetOTPVerifyResponse:
    """
    Verify the 6-digit OTP from Step 1.

    On success:
    - The `reset_token` is promoted (`otp_verified = true` in Redis).
    - Pass the **same** `reset_token` to `/password/forgot/reset`.

    After **5 consecutive wrong codes** the session is destroyed and the user
    must restart from Step 1.
    """
    result = await svc.verify_password_reset_otp(
        reset_token=body.reset_token,
        otp_code=body.otp_code,
    )
    return PasswordResetOTPVerifyResponse(
        reset_token=result["reset_token"],
        message=result["message"],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Forgot password — Step 3: set new password
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/forgot/reset",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Forgot password — Step 3: set new password",
    responses={
        400: {"description": "Password does not meet policy / passwords do not match"},
        400: {"description": "OTP not yet verified — complete Step 2 first"},
        410: {"description": "Reset session expired or already used"},
    },
)
async def forgot_password_reset(
    body: PasswordResetCompleteRequest,
    svc:  UserServiceDep,
) -> MessageResponse:
    """
    Set a new password using the promoted `reset_token` from Step 2.

    On success:
    - The new password (Argon2id-hashed) replaces the old one.
    - All existing DB password reset tokens for this user are invalidated.
    - The Redis reset session is deleted (single-use).
    - The user must log in again with the new password.

    Password policy:
    - Minimum 8 characters
    - At least one uppercase (A–Z), lowercase (a–z), digit (0–9),
      and special character (!@#$%^&*…)
    """
    await svc.complete_password_reset(
        reset_token=body.reset_token,
        new_password=body.new_password,
    )
    return MessageResponse(
        message="Password reset successfully. Please log in with your new password."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Change password (authenticated)
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/change",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Change password (authenticated user)",
    responses={
        400: {"description": "Current password incorrect / new password policy violation"},
        401: {"description": "Not authenticated"},
        409: {"description": "No password set — use /auth/social/set-password instead"},
    },
)
async def change_password(
    body: ChangePasswordRequest,
    svc:  UserServiceDep,
    user: Annotated[User, Depends(require_active_user)],
) -> MessageResponse:
    """
    Change the password for the currently authenticated user.

    Requires the existing password for verification before accepting the new
    one. On success, **all other active sessions** (other devices) are
    terminated.  The current session's access token remains valid until its
    natural expiry.

    If the account was created via OAuth and has no password set, use
    `POST /auth/social/set-password` instead.
    """
    await svc.change_password(
        user=user,
        current_pass=body.current_password,
        new_pass=body.new_password,
    )
    return MessageResponse(
        message="Password changed. All other sessions have been terminated."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Set first password — channel-registered accounts
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/channel/set-password",
    status_code=status.HTTP_200_OK,
    summary="Set first password for a channel-registered account (SMS/WhatsApp/Call)",
)
async def channel_set_password(
    body: dict,
    svc:  UserServiceDep,
    user: Annotated[object, Depends(require_active_user_or_channel)],
) -> dict:
    """
    Completes the PAP account upgrade after channel login.

    Called after:
      POST /auth/channel-login/verify-otp → returns must_set_password: true
      (client shows set-password screen)
      POST /auth/channel/set-password      ← this endpoint
      → status CHANNEL_REGISTERED → ACTIVE
      → full account active, all platform features available

    No current_password required — phone ownership was proven at:
      1. Channel registration (PAP initiated the SMS/WhatsApp conversation)
      2. Login OTP (verified in /auth/channel-login/verify-otp)

    Request body:
      new_password  — must meet platform password policy

    Response:
      message, user_id, status → "active"
    """
    await svc.set_password_for_channel_user(
        user     = user,
        new_pass = body.get("new_password", ""),
    )
    return {
        "message": "Password set. Your account is now fully active.",
        "user_id": str(user.id),
        "status":  "active",
    }

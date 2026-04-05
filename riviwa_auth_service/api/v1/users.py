"""
app/api/v1/users.py
═══════════════════════════════════════════════════════════════════════════════
User profile endpoints (authenticated — personal view only).

Routes
──────
  GET    /api/v1/users/me           Full private profile
  PATCH  /api/v1/users/me           Update profile fields
  DELETE /api/v1/users/me           Soft-delete account (deactivate)
  POST   /api/v1/users/me/avatar    Update avatar URL
  POST   /api/v1/users/me/verify-email   Re-trigger email verification
  POST   /api/v1/users/me/verify-phone   Trigger phone verification

Admin routes (platform_role = admin | super_admin):
  POST   /api/v1/users/{user_id}/suspend
  POST   /api/v1/users/{user_id}/ban
  POST   /api/v1/users/{user_id}/reactivate
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, status

from api.v1.deps import UserServiceDep
from core.dependencies import require_active_user, require_platform_role
from models.user import User
from schemas.common import MessageResponse
from schemas.user import (
    UserAvatarUpdateRequest,
    UserPrivateResponse,
    UserUpdateRequest,
)

router = APIRouter(prefix="/users", tags=["Users"])


# ─────────────────────────────────────────────────────────────────────────────
# GET /me — private profile
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/me",
    response_model=UserPrivateResponse,
    status_code=status.HTTP_200_OK,
    summary="Get my profile",
    responses={401: {"description": "Not authenticated"}},
)
async def get_me(
    user: Annotated[User, Depends(require_active_user)],
) -> UserPrivateResponse:
    """
    Return the full private profile for the authenticated user.

    Includes verification flags, OAuth status, active org context,
    and all profile fields.  Security-sensitive fields
    (`hashed_password`, `two_factor_secret`) are excluded.
    """
    return UserPrivateResponse.model_validate(
        {
            **user.__dict__,
            "has_password": user.hashed_password is not None,
        }
    )


# ─────────────────────────────────────────────────────────────────────────────
# PATCH /me — update profile
# ─────────────────────────────────────────────────────────────────────────────

@router.patch(
    "/me",
    response_model=UserPrivateResponse,
    status_code=status.HTTP_200_OK,
    summary="Update my profile",
    responses={
        400: {"description": "Validation error"},
        401: {"description": "Not authenticated"},
        409: {"description": "Username already taken"},
    },
)
async def update_me(
    body: UserUpdateRequest,
    svc:  UserServiceDep,
    user: Annotated[User, Depends(require_active_user)],
) -> UserPrivateResponse:
    """
    Update one or more profile fields (PATCH semantics — only supplied fields
    are changed).

    Fields managed by dedicated endpoints and **not** accepted here:
    - `email` / `phone_number` (require OTP verification flows)
    - `password` → use `/auth/password/change`
    - `avatar_url` → use `/users/me/avatar`
    - `status` → admin-only
    """
    updates = body.model_dump(exclude_none=True)
    updated_user = await svc.update_profile(user=user, updates=updates)
    return UserPrivateResponse.model_validate(
        {
            **updated_user.__dict__,
            "has_password": updated_user.hashed_password is not None,
        }
    )


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /me — deactivate account
# ─────────────────────────────────────────────────────────────────────────────

@router.delete(
    "/me",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Deactivate my account",
    responses={401: {"description": "Not authenticated"}},
)
async def deactivate_me(
    svc:  UserServiceDep,
    user: Annotated[User, Depends(require_active_user)],
) -> MessageResponse:
    """
    Soft-delete the authenticated user's account.

    - Account status → `DEACTIVATED` (reversible by a platform admin).
    - All active sessions are terminated.
    - The account is no longer accessible for login.

    This is **not** a hard delete — the User row and all related data
    are retained for compliance and audit purposes.
    """
    await svc.deactivate(user=user)
    return MessageResponse(
        message="Your account has been deactivated. Contact support to reactivate."
    )


# ─────────────────────────────────────────────────────────────────────────────
# POST /me/avatar — update avatar
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/me/avatar",
    response_model=UserPrivateResponse,
    status_code=status.HTTP_200_OK,
    summary="Update avatar URL",
    responses={
        400: {"description": "URL is not HTTPS"},
        401: {"description": "Not authenticated"},
    },
)
async def update_avatar(
    body: UserAvatarUpdateRequest,
    svc:  UserServiceDep,
    user: Annotated[User, Depends(require_active_user)],
) -> UserPrivateResponse:
    """
    Set or clear the profile avatar.

    `avatar_url` must point to an already-uploaded image (HTTPS only).
    Upload the image first using a pre-signed S3 URL from the media service,
    then call this endpoint with the resulting CDN URL.

    Pass `avatar_url = null` to clear the avatar and revert to the default
    initials avatar.
    """
    updates = {"avatar_url": body.avatar_url}
    updated_user = await svc.update_profile(user=user, updates=updates)
    return UserPrivateResponse.model_validate(
        {
            **updated_user.__dict__,
            "has_password": updated_user.hashed_password is not None,
        }
    )


# ─────────────────────────────────────────────────────────────────────────────
# POST /me/verify-email — re-trigger email verification
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/me/verify-email",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark email as verified (post-registration)",
    responses={401: {"description": "Not authenticated"}},
)
async def verify_email(
    svc:  UserServiceDep,
    user: Annotated[User, Depends(require_active_user)],
) -> MessageResponse:
    """
    Mark the authenticated user's email address as verified.

    Called after the user completes an OTP flow from the standalone
    `/auth/otp/send` + `/auth/otp/verify` endpoints with `purpose = email_verify`.

    In the full flow the OTP endpoint calls this automatically on success;
    this endpoint is exposed for direct use in testing and admin tools.
    """
    await svc.verify_email(user=user)
    return MessageResponse(message="Email address verified.")


# ─────────────────────────────────────────────────────────────────────────────
# POST /me/verify-phone — trigger phone verification
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/me/verify-phone",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark phone as verified (post-registration)",
    responses={401: {"description": "Not authenticated"}},
)
async def verify_phone(
    svc:  UserServiceDep,
    user: Annotated[User, Depends(require_active_user)],
) -> MessageResponse:
    """
    Mark the authenticated user's phone number as verified.

    Same lifecycle as `verify_email` — call after a successful
    `phone_verify` OTP flow.
    """
    await svc.verify_phone(user=user)
    return MessageResponse(message="Phone number verified.")


# ─────────────────────────────────────────────────────────────────────────────
# Admin — suspend / ban / reactivate
# ─────────────────────────────────────────────────────────────────────────────

_admin_guard = Depends(require_platform_role("admin"))


@router.post(
    "/{user_id}/suspend",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="[Admin] Suspend a user account",
    dependencies=[_admin_guard],
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Insufficient platform role"},
        404: {"description": "User not found"},
    },
)
async def admin_suspend_user(
    user_id: uuid.UUID,
    svc:     UserServiceDep,
    reason:  Optional[str] = None,
) -> MessageResponse:
    """
    Set the user's account status to `SUSPENDED`.

    Suspended accounts cannot log in. The user sees a `AccountSuspendedError`
    on next auth attempt.  Use `reactivate` to lift the suspension.

    Requires `platform_role = admin` or `super_admin`.
    """
    await svc.suspend(user_id=user_id, reason=reason)
    return MessageResponse(message=f"User {user_id} has been suspended.")


@router.post(
    "/{user_id}/ban",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="[Admin] Permanently ban a user account",
    dependencies=[_admin_guard],
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Insufficient platform role"},
        404: {"description": "User not found"},
    },
)
async def admin_ban_user(
    user_id: uuid.UUID,
    svc:     UserServiceDep,
    reason:  Optional[str] = None,
) -> MessageResponse:
    """
    Set the user's account status to `BANNED`.

    A ban is more permanent than a suspension. Banned accounts cannot log in.
    Use `reactivate` to restore access if the ban is lifted by a moderator.

    Requires `platform_role = admin` or `super_admin`.
    """
    await svc.ban(user_id=user_id, reason=reason)
    return MessageResponse(message=f"User {user_id} has been banned.")


@router.post(
    "/{user_id}/reactivate",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="[Admin] Reactivate a suspended or deactivated user",
    dependencies=[_admin_guard],
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Insufficient platform role"},
        404: {"description": "User not found"},
    },
)
async def admin_reactivate_user(
    user_id: uuid.UUID,
    svc:     UserServiceDep,
) -> MessageResponse:
    """
    Restore a `SUSPENDED` or `DEACTIVATED` account to `ACTIVE`.

    Cannot be used to un-ban (`BANNED`) accounts — contact the trust & safety
    team for ban reviews.

    Requires `platform_role = admin` or `super_admin`.
    """
    await svc.reactivate(user_id=user_id)
    return MessageResponse(message=f"User {user_id} has been reactivated.")

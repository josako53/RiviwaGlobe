"""
app/api/v1/register.py
═══════════════════════════════════════════════════════════════════════════════
Account registration endpoints — email/phone 3-step flow.

Routes
──────
  POST /api/v1/auth/register/init          Step 1 — submit identifier, start OTP
  POST /api/v1/auth/register/verify-otp    Step 2 — verify OTP
  POST /api/v1/auth/register/complete      Step 3 — set password, activate account
  POST /api/v1/auth/register/resend-otp    Resend OTP for an active Step 1 session
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, status

from api.v1.deps import RegistrationServiceDep
from core.dependencies import get_client_ip, get_user_agent
from schemas.auth.register import OTPResendRequest, OTPResendResponse
from services.registration_service import (
    CompleteRequest,
    InitiateRequest,
    InitiateResponse,
    VerifyOTPRequest,
    VerifyOTPResponse,
)

router = APIRouter(prefix="/auth/register", tags=["Registration"])


# ─────────────────────────────────────────────────────────────────────────────
# Step 1 — initiate
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/init",
    response_model=InitiateResponse,
    status_code=status.HTTP_200_OK,
    summary="Register — Step 1: submit email or phone",
    responses={
        400: {"description": "Invalid identifier format"},
        409: {"description": "Email / phone / username already registered"},
        422: {"description": "Validation error (e.g. both email and phone supplied)"},
        403: {"description": "Registration blocked by fraud engine"},
    },
)
async def register_init(
    body:       InitiateRequest,
    svc:        RegistrationServiceDep,
    ip_address: Annotated[str,          Depends(get_client_ip)],
    user_agent: Annotated[Optional[str], Depends(get_user_agent)],
) -> InitiateResponse:
    """
    Begin account registration.

    Supply **exactly one** of `email` or `phone_number`. The server:

    1. Validates uniqueness (rejects if the identifier is already registered).
    2. Runs the fraud-scoring engine against the supplied signals.
       - `BLOCK` → HTTP 403 (`FraudBlockedError`).
       - `ALLOW` / `REVIEW` → proceed; REVIEW triggers ID verification after Step 3.
    3. Creates a bare `User` row (no password yet).
    4. Sends a 6-digit OTP via email or SMS.
    5. Returns a `session_token` that must be echoed in Step 2.

    The `session_token` expires after **10 minutes**. Call `/register/resend-otp`
    if the user does not receive the code within that window.
    """
    return await svc.initiate(
        data=body,
        ip_address=ip_address,
        user_agent=user_agent,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Step 2 — OTP verification
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/verify-otp",
    response_model=VerifyOTPResponse,
    status_code=status.HTTP_200_OK,
    summary="Register — Step 2: verify OTP",
    responses={
        400: {"description": "Invalid OTP (wrong code — increment attempt counter)"},
        410: {"description": "OTP expired or session not found — restart from Step 1"},
        429: {"description": "Maximum OTP attempts exceeded — session destroyed"},
    },
)
async def register_verify_otp(
    body: VerifyOTPRequest,
    svc:  RegistrationServiceDep,
) -> VerifyOTPResponse:
    """
    Verify the 6-digit code delivered in Step 1.

    On success:
    - The identifier (email or phone) is marked **verified** on the User row.
    - The Step 1 session token is consumed (single-use).
    - A short-lived `continuation_token` is returned.

    Pass `continuation_token` to Step 3 (`/register/complete`).
    It expires after **30 minutes**.

    After **5 consecutive wrong codes** the session is destroyed and
    HTTP 429 is returned — the user must restart from Step 1.
    """
    return await svc.verify_otp(data=body)


# ─────────────────────────────────────────────────────────────────────────────
# Step 3 — complete registration
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/complete",
    status_code=status.HTTP_201_CREATED,
    summary="Register — Step 3: set password and activate account",
    responses={
        400: {"description": "Weak password / password policy violation"},
        410: {"description": "Continuation token expired — restart registration"},
    },
)
async def register_complete(
    body:       CompleteRequest,
    svc:        RegistrationServiceDep,
    ip_address: Annotated[str, Depends(get_client_ip)],
):
    """
    Set the account password and activate the user.

    On success:
    - Password is Argon2id-hashed and stored.
    - Account status transitions to `ACTIVE`
      (unless fraud score triggered `REVIEW`, in which case it stays
      `PENDING_ID` until government ID verification completes).
    - The continuation token is consumed.

    **`action` field in the response:**
    - `"complete"` → account is active; proceed to login.
    - `"id_verification_pending"` → account needs ID verification.
      Present the user with the ID verification URL from the response.
    """
    return await svc.complete(data=body, ip_address=ip_address)


# ─────────────────────────────────────────────────────────────────────────────
# OTP resend
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/resend-otp",
    response_model=InitiateResponse,
    status_code=status.HTTP_200_OK,
    summary="Register — resend OTP",
    responses={
        410: {"description": "Session expired — restart from Step 1"},
        429: {"description": "Resend cooldown active (60 s minimum between resends)"},
    },
)
async def register_resend_otp(
    body: OTPResendRequest,
    svc:  RegistrationServiceDep,
) -> InitiateResponse:
    """
    Request a new OTP for an active registration session.

    A **60-second cooldown** is enforced between resends.
    The old OTP is invalidated immediately and a fresh 6-digit code is sent.
    The session TTL is **not** extended on resend.

    Returns a new `session_token` — the old one is consumed; use the new one
    in Step 2.
    """
    return await svc.resend_otp(session_token=body.session_token)

"""
api/v1/channel_auth.py
═══════════════════════════════════════════════════════════════════════════════
Authentication flows for channel-registered Consumers.

Channel registration:
  When a Consumer first contacts via SMS, WhatsApp, or Call, their phone number
  is already verified by the act of initiating the conversation.
  No OTP is needed, no password is set.
  A minimal User account (status=CHANNEL_REGISTERED) is auto-created
  and tokens are issued immediately so the feedback submission is linked.

Upgrading to full account:
  When a channel-registered Consumer later opens the mobile app or web portal,
  they go through a 2-step upgrade flow:
    Step 1  POST /auth/channel-login/request-otp
            → server sends OTP to their verified phone
    Step 2  POST /auth/channel-login/verify-otp
            → OTP verified → returns tokens + "must_set_password": true
    Step 3  POST /auth/password/change   (existing endpoint, no current password needed
                                          for CHANNEL_REGISTERED accounts)
            → password set → account upgrades to ACTIVE

Routes
───────
  POST /auth/channel-register          Internal — called by feedback_service on first inbound message
  POST /auth/channel-login/request-otp Step 1 — Consumer wants app access, sends OTP to their phone
  POST /auth/channel-login/verify-otp  Step 2 — verify OTP → tokens (+ must_set_password flag)

Security notes:
  · channel-register is marked internal — only callable from feedback_service
    via the shared service-to-service API key (X-Service-Key header).
  · No OTP on channel-register: the inbound message itself is proof of ownership.
  · The CHANNEL_REGISTERED status means the account is usable (can receive tokens,
    link feedback) but the login flow tells the client "must_set_password: true"
    until a password is set and status → ACTIVE.
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import re
import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.deps import get_db, get_publisher
from core.config import settings
from core.dependencies import get_client_ip
from core.exceptions import (
    ConflictError,
    InvalidOTPError,
    NotFoundError,
    UnauthorisedError,
    ValidationError,
)
from core.security import create_access_token, generate_refresh_token
from models.user import AccountStatus, User
from repositories.user_repository import UserRepository
from events.publisher import EventPublisher

router = APIRouter(prefix="/auth", tags=["Channel Auth"])

# Shared secret that feedback_service must send when calling channel-register.
# Set in .env as INTERNAL_SERVICE_KEY.
_SERVICE_KEY = getattr(settings, "INTERNAL_SERVICE_KEY", "change-me-in-env")


def _require_service_key(x_service_key: str = Header(..., alias="X-Service-Key")) -> None:
    if x_service_key != _SERVICE_KEY:
        raise UnauthorisedError()


# ─────────────────────────────────────────────────────────────────────────────
# Channel registration (internal — called by feedback_service)
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/channel-register",
    status_code=status.HTTP_200_OK,
    summary="[Internal] Auto-register a Consumer from an inbound channel message",
    dependencies=[Depends(_require_service_key)],
)
async def channel_register(
    body:      dict,
    db:        AsyncSession   = Depends(get_db),
    publisher: EventPublisher = Depends(get_publisher),
) -> dict:
    """
    Called by feedback_service when an inbound SMS/WhatsApp/Call message
    arrives from a phone number not yet in the system.

    Because the Consumer initiated the conversation, ownership of the phone
    number is already proven — no OTP is needed.

    Behaviour:
      · If phone_number already has an account → return existing user_id + tokens.
        (idempotent — feedback_service may call this on every session start)
      · If phone_number is new → create User(status=CHANNEL_REGISTERED,
        phone_verified=True, hashed_password=None, registration_source=channel)
        and return tokens.

    Request body:
      phone_number  — E.164 e.g. "+255712345678"
      channel       — "sms" | "whatsapp" | "phone_call"
      display_name  — optional, extracted by LLM during conversation
      language      — "sw" | "en" (detected from first message)

    Response:
      user_id, access_token, refresh_token, is_new_user
    """
    phone_number = body.get("phone_number", "").strip()
    if not re.match(r"^\+[1-9]\d{7,14}$", phone_number):
        raise ValidationError("phone_number must be in E.164 format.")

    channel = body.get("channel", "sms")
    repo    = UserRepository(db)

    # ── Idempotent: return existing if already registered ─────────────────────
    existing_user = await repo.get_by_phone(phone_number)
    if existing_user:
        # Issue fresh tokens for the existing user
        tokens = await _issue_tokens(existing_user, db)
        return {
            "user_id":      str(existing_user.id),
            "is_new_user":  False,
            "must_set_password": existing_user.status == AccountStatus.CHANNEL_REGISTERED,
            **tokens,
        }

    # ── New user — create channel-registered account ──────────────────────────
    # Auto-generate username from phone (masked for display)
    base_username = "consumer_" + re.sub(r"\D", "", phone_number)[-8:]
    username      = base_username
    suffix        = 1
    while await repo.get_by_username(username):
        username = f"{base_username}_{suffix}"
        suffix  += 1

    new_user = await repo.create(
        username             = username,
        phone_number         = phone_number,
        phone_verified       = True,      # proved by initiating the conversation
        hashed_password      = None,      # no password at channel registration stage
        display_name         = body.get("display_name"),
        full_name            = body.get("full_name"),
        language             = body.get("language", "sw"),
        status               = AccountStatus.CHANNEL_REGISTERED,
        registration_source  = channel,
    )
    await db.commit()

    # Publish user.registered event
    await publisher.user_registered(new_user.id, channel)

    tokens = await _issue_tokens(new_user, db)

    return {
        "user_id":           str(new_user.id),
        "is_new_user":       True,
        "must_set_password": True,
        **tokens,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Channel login — Step 1: request OTP
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/channel-login/request-otp",
    status_code=status.HTTP_200_OK,
    summary="Channel login Step 1 — send OTP to a channel-registered phone",
)
async def channel_login_request_otp(
    body: dict,
    db:   AsyncSession = Depends(get_db),
) -> dict:
    """
    A Consumer who registered via SMS/WhatsApp now wants to log in through the
    mobile app or web portal.

    Sends a 6-digit OTP to their verified phone number.
    Returns a session_token to pass to Step 2.

    Request body:
      phone_number  — E.164

    This endpoint also works for fully ACTIVE accounts so the same login
    screen handles both first-time password setup and returning users.
    """
    phone_number = body.get("phone_number", "").strip()
    if not re.match(r"^\+[1-9]\d{7,14}$", phone_number):
        raise ValidationError("phone_number must be in E.164 format.")

    repo = UserRepository(db)
    user = await repo.get_by_phone(phone_number)
    if not user:
        # Return same response regardless — don't reveal whether number exists
        return {
            "session_token": _make_dummy_session(),
            "message":       "If this number is registered, an OTP has been sent.",
            "expires_in":    300,
        }

    if user.status in (AccountStatus.BANNED, AccountStatus.SUSPENDED):
        raise UnauthorisedError()

    # Generate and store OTP
    import secrets, hashlib
    from datetime import datetime, timedelta, timezone
    otp_code    = f"{secrets.randbelow(1000000):06d}"
    otp_hash    = hashlib.sha256(otp_code.encode()).hexdigest()
    session_tok = secrets.token_urlsafe(32)

    # Store in Redis: otp_session:<token> → {user_id, otp_hash, expires_at}
    redis_client = await _get_redis()
    await redis_client.setex(
        f"channel_otp:{session_tok}",
        300,  # 5 minutes
        f"{user.id}:{otp_hash}",
    )

    # Send OTP via SMS
    try:
        provider = get_sms_provider()
        await provider.send(recipient=phone_number, message=msg, purpose="channel_login")
    except Exception as exc:
        log.error("channel_auth.otp_send_failed", phone=phone_number[:6]+"****", error=str(exc))

    return {
        "session_token": session_tok,
        "message":       "OTP sent to your registered phone number.",
        "expires_in":    300,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Channel login — Step 2: verify OTP
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/channel-login/verify-otp",
    status_code=status.HTTP_200_OK,
    summary="Channel login Step 2 — verify OTP and receive tokens",
)
async def channel_login_verify_otp(
    body:      dict,
    db:        AsyncSession = Depends(get_db),
    ip:        str          = Depends(get_client_ip),
) -> dict:
    """
    Verifies the OTP from Step 1 and issues access + refresh tokens.

    If the account is still CHANNEL_REGISTERED (no password set yet),
    the response includes "must_set_password": true and "next_step": "set_password".
    The client must redirect to the set-password screen.
    After the user sets a password:
      POST /api/v1/auth/password/change  (existing endpoint)
      → This will be extended to handle CHANNEL_REGISTERED accounts
        (no current_password required, just new_password + session token)
      → Account status upgrades to ACTIVE.

    Request body:
      session_token — from Step 1
      otp_code      — 6-digit code

    Response:
      access_token, refresh_token, must_set_password, user_id
    """
    session_tok = body.get("session_token", "").strip()
    otp_code    = body.get("otp_code", "").strip()

    if not session_tok or not otp_code:
        raise ValidationError("session_token and otp_code are required.")
    if not re.match(r"^\d{6}$", otp_code):
        raise InvalidOTPError()

    redis_client = await _get_redis()
    stored = await redis_client.get(f"channel_otp:{session_tok}")
    if not stored:
        raise InvalidOTPError()

    import json
    from core.notifications import get_provider_for_channel
    stored_str  = stored.decode() if isinstance(stored, bytes) else stored
    session_data = json.loads(stored_str)
    user_id_str  = session_data["user_id"]

    provider = get_provider_for_channel("sms")
    try:
        code_is_valid = await provider.verify_otp(
            submitted_code  = otp_code,
            session_payload = session_data,
        )
    except Exception:
        code_is_valid = False

    if not code_is_valid:
        raise InvalidOTPError()

    # Consume the OTP session
    await redis_client.delete(f"channel_otp:{session_tok}")

    repo = UserRepository(db)
    user = await repo.get_by_id(uuid.UUID(user_id_str))
    if not user:
        raise NotFoundError()

    tokens = await _issue_tokens(user, db)
    must_set_password = user.status == AccountStatus.CHANNEL_REGISTERED

    return {
        "user_id":           str(user.id),
        "must_set_password": must_set_password,
        "next_step":         "set_password" if must_set_password else None,
        "message": (
            "Please set a password to complete your account setup."
            if must_set_password else
            "Login successful."
        ),
        **tokens,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _issue_tokens(user: User, db: AsyncSession) -> dict:
    """Issue JWT + refresh token for a user."""
    from core.dependencies import get_redis as _get_r
    redis = await _get_redis()

    token, jti, expires_in = create_access_token(
        user_id       = user.id,
        org_id        = None,
        org_role      = None,
        platform_role = None,
    )
    refresh = generate_refresh_token()
    _REFRESH_PREFIX = "refresh:"
    await redis.setex(
        f"{_REFRESH_PREFIX}{refresh}",
        60 * 60 * 24 * 30,  # 30 days
        str(user.id),
    )
    return {
        "access_token":  token,
        "refresh_token": refresh,
        "token_type":    "bearer",
        "expires_in":    expires_in,
    }


async def _get_redis():
    """Grab the shared Redis connection."""
    from db.session import get_redis_client
    return await get_redis_client()


def _make_dummy_session() -> str:
    """Return a fake session token for non-existent users (timing-safe)."""
    import secrets
    return secrets.token_urlsafe(32)

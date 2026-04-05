"""
services/user_service.py
═══════════════════════════════════════════════════════════════════════════════
User lifecycle operations after the initial registration pipeline.

Each public method:
  1. Validates business rules
  2. Delegates DB writes to UserRepository (flush only)
  3. Commits via the injected AsyncSession
  4. Publishes a Kafka event via EventPublisher

Password reset flow (Redis-based OTP)
──────────────────────────────────────
  initiate_password_reset()      Step 1 — generate OTP, store in Redis
  verify_password_reset_otp()    Step 2 — verify OTP, promote session
  complete_password_reset()      Step 3 — set new password, consume session
  reset_password_with_token()    DB-token path (email link; kept for compat)

Redis key schema (password reset)
───────────────────────────────────
  pwd_reset:<reset_token>  →  JSON  TTL = OTP_PASSWORD_RESET_TTL_SECONDS (600 s)
    {
        user_id:       str,
        otp_verified:  bool,
        attempts:      int,
        channel:       str,   # "email" | "sms"
        # + provider_payload fields (provider-dependent):
        #   twilio_verify → { provider, to, channel, verification_sid }
        #   twilio_sms    → { provider, to, otp_hash, message_sid }
        #   smtp / stub   → { provider, to, otp_hash }
    }

Kafka events published
──────────────────────
  user.email_verified
  user.phone_verified
  user.suspended | banned | deactivated | reactivated
  user.password_changed
  user.password_reset
  user.profile_updated
  user.oauth_linked
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.exceptions import (
    InvalidOTPError,
    InvalidTokenError,
    OTPExpiredError,
    OTPMaxAttemptsError,
    PasswordAlreadySetError,
    PasswordMismatchError,
    PasswordNotSetError,
    SamePasswordError,
    UserNotFoundError,
    WeakPasswordError,
)
from core.notifications import get_provider_for_channel
from core.security import (
    generate_secure_token,
    hash_password,
    hash_token,
    validate_password_strength,
    verify_password,
)
from events.publisher import EventPublisher
from events.topics import UserEvents
from models.user import AccountStatus, User
from repositories.password_reset_repository import PasswordResetRepository
from repositories.user_repository import UserRepository

log = structlog.get_logger(__name__)

# ── Redis key prefix ──────────────────────────────────────────────────────────
_PWD_RESET_PREFIX   = "pwd_reset:"
_PWD_RESET_TTL      = getattr(settings, "OTP_PASSWORD_RESET_TTL_SECONDS", 600)
_OTP_MAX_ATTEMPTS   = getattr(settings, "OTP_MAX_ATTEMPTS", 5)


class UserService:

    def __init__(
        self,
        db:        AsyncSession,
        publisher: EventPublisher,
        redis:     Optional[Redis] = None,
    ) -> None:
        self.db            = db
        self.publisher     = publisher
        self.redis         = redis
        self.user_repo     = UserRepository(db)
        self.pw_reset_repo = PasswordResetRepository(db)

    # ── Email verification ────────────────────────────────────────────────────

    async def verify_email(self, user: User) -> User:
        """
        Mark the authenticated user's email address as verified.
        Called by the OTP service or directly by the test/admin shortcut.
        """
        await self.user_repo.mark_email_verified(user.id)
        await self.db.commit()
        user = await self.user_repo.get_by_id(user.id)
        log.info("user.email_verified", user_id=str(user.id))
        await self.publisher.user_email_verified(user)
        return user

    async def verify_phone(self, user: User) -> User:
        """Mark phone_verified=True, commit, publish user.phone_verified."""
        await self.user_repo.mark_phone_verified(user.id)
        await self.db.commit()
        user = await self.user_repo.get_by_id(user.id)
        log.info("user.phone_verified", user_id=str(user.id))
        await self.publisher.user_phone_verified(user)
        return user

    # ── Password management ───────────────────────────────────────────────────

    async def change_password(
        self,
        user:         User,
        current_pass: str,
        new_pass:     str,
    ) -> None:
        """
        Change password for a user who already has one set.
        Verifies current password before accepting new one.
        On success: stores new hash, invalidates all reset tokens, commits,
        publishes user.password_changed.
        """
        if not user.hashed_password:
            raise PasswordNotSetError()

        if not verify_password(current_pass, user.hashed_password):
            raise PasswordMismatchError()

        if verify_password(new_pass, user.hashed_password):
            raise SamePasswordError()

        ok, reason = validate_password_strength(new_pass)
        if not ok:
            raise WeakPasswordError(reason)

        new_hash = hash_password(new_pass)
        await self.user_repo.set_password(user.id, new_hash)
        await self.pw_reset_repo.invalidate_all_for_user(user.id)
        await self.db.commit()

        log.info("user.password_changed", user_id=str(user.id))
        await self.publisher.user_password_changed(user, all_sessions_revoked=True)

    async def set_password_for_oauth_user(
        self,
        user:     User,
        new_pass: str,
    ) -> None:
        """Set a first password on an OAuth-only account (no existing password)."""
        if user.hashed_password:
            raise PasswordAlreadySetError()

        ok, reason = validate_password_strength(new_pass)
        if not ok:
            raise WeakPasswordError(reason)

        new_hash = hash_password(new_pass)
        await self.user_repo.set_password(user.id, new_hash)
        await self.db.commit()

        log.info("user.password_set", user_id=str(user.id))
        await self.publisher.user_password_changed(user, all_sessions_revoked=False)

    async def set_password_for_channel_user(
        self,
        user:     User,
        new_pass: str,
    ) -> None:
        """
        Set a first password for a CHANNEL_REGISTERED account and upgrade
        status to ACTIVE.

        Called when a PAP who registered via SMS/WhatsApp/Call logs in for
        the first time through the mobile app or web portal.

        Rules:
          · User must be CHANNEL_REGISTERED (no password set, phone verified).
          · No current_password required — phone ownership was proven at
            channel registration time and again via OTP in the login flow.
          · After success: status → ACTIVE, password set, event published.
        """
        from models.user import AccountStatus
        if user.status != AccountStatus.CHANNEL_REGISTERED:
            raise ValidationError(
                "This endpoint is only for channel-registered accounts. "
                "Use /auth/password/change if you already have a password."
            )
        if user.hashed_password:
            raise PasswordAlreadySetError()

        ok, reason = validate_password_strength(new_pass)
        if not ok:
            raise WeakPasswordError(reason)

        new_hash = hash_password(new_pass)
        await self.user_repo.set_password(user.id, new_hash)

        # Upgrade account status to ACTIVE
        user.status = AccountStatus.ACTIVE
        self.db.add(user)
        await self.db.commit()

        log.info(
            "user.channel_account_activated",
            user_id=str(user.id),
            registration_source=user.registration_source,
        )
        await self.publisher.user_password_changed(user, all_sessions_revoked=False)

    # ── Forgot password — Redis OTP flow ──────────────────────────────────────

    async def initiate_password_reset(
        self,
        identifier: str,
        ip_address: str,
    ) -> dict:
        """
        Step 1 — begin the forgot-password flow.

        Always returns HTTP 200 regardless of whether an account was found
        (prevents account enumeration).  If no active account matches, the
        operation is silently ignored — a dummy reset_token is returned but
        no OTP is sent.

        Redis key: pwd_reset:<reset_token>
        TTL: OTP_PASSWORD_RESET_TTL_SECONDS (600 s = 10 min)

        Returns a dict matching PasswordResetInitResponse:
            {
                reset_token,
                otp_channel,
                otp_destination,
                expires_in_seconds,
                message,
            }
        """
        assert self.redis is not None, (
            "UserService requires redis to be injected for password reset. "
            "Update get_user_service() in deps.py."
        )

        # Dummy values returned when no account is found
        dummy_token  = generate_secure_token()
        dummy_dest   = "if***@exists.com"
        dummy_channel = "email"

        # Try to find the account
        user = await self.user_repo.get_by_identifier(identifier)

        if not user or user.status != AccountStatus.ACTIVE:
            # Silent no-op: return success with dummy data (anti-enumeration)
            log.info(
                "password_reset.no_active_account",
                identifier_type="email" if "@" in identifier else "phone",
            )
            return {
                "reset_token":        dummy_token,
                "otp_channel":        dummy_channel,
                "otp_destination":    dummy_dest,
                "expires_in_seconds": _PWD_RESET_TTL,
                "message": (
                    "If an account with that identifier exists, "
                    "a verification code has been sent."
                ),
            }

        # Invalidate all existing DB reset tokens for this user
        await self.pw_reset_repo.invalidate_all_for_user(user.id)
        await self.db.commit()

        # Determine channel
        if identifier.startswith("+") and user.phone_number:
            channel     = "sms"
            to          = user.phone_number
            destination = _mask_phone(user.phone_number)
        else:
            channel     = "email"
            to          = user.email
            destination = _mask_email(user.email)

        reset_token = generate_secure_token()

        # ── Dispatch OTP via configured provider ──────────────────────────
        provider         = get_provider_for_channel(channel)
        provider_payload = await provider.send_otp(
            to=to,
            channel=channel,
            display_name=user.display_name,
            purpose="password_reset",
        )

        # ── Store session in Redis ─────────────────────────────────────────
        session = {
            "user_id":      str(user.id),
            "otp_verified": False,
            "attempts":     0,
            "channel":      channel,
            **provider_payload,
        }
        await self.redis.setex(
            f"{_PWD_RESET_PREFIX}{reset_token}",
            _PWD_RESET_TTL,
            json.dumps(session),
        )

        log.info(
            "password_reset.otp_dispatched",
            user_id=str(user.id),
            channel=channel,
            ip=ip_address,
            provider=provider_payload.get("provider"),
        )

        return {
            "reset_token":        reset_token,
            "otp_channel":        channel,
            "otp_destination":    destination,
            "expires_in_seconds": _PWD_RESET_TTL,
            "message": (
                "If an account with that identifier exists, "
                "a verification code has been sent."
            ),
        }

    async def verify_password_reset_otp(
        self,
        reset_token: str,
        otp_code:    str,
    ) -> dict:
        """
        Step 2 — verify the OTP from Step 1.

        On success: sets otp_verified=True in the Redis session and returns
        the promoted reset_token for use in Step 3.

        On failure: increments the attempt counter; after 5 wrong codes the
        session is deleted and the user must restart from Step 1.

        Returns a dict matching PasswordResetOTPVerifyResponse:
            { reset_token, message }
        """
        assert self.redis is not None

        redis_key = f"{_PWD_RESET_PREFIX}{reset_token}"
        raw       = await self.redis.get(redis_key)

        if not raw:
            raise OTPExpiredError()

        session  = json.loads(raw)
        attempts = session.get("attempts", 0)

        # Max-attempts guard
        if attempts >= _OTP_MAX_ATTEMPTS:
            await self.redis.delete(redis_key)
            raise OTPMaxAttemptsError()

        # ── OTP verification — delegates to the originating provider ─────
        provider = get_provider_for_channel(session["channel"])
        try:
            code_is_valid = await provider.verify_otp(
                submitted_code=otp_code,
                session_payload=session,
            )
        except Exception:
            raise  # OTPExpiredError / OTPMaxAttemptsError bubble from Twilio

        if not code_is_valid:
            attempts += 1
            session["attempts"] = attempts

            if attempts >= _OTP_MAX_ATTEMPTS:
                await self.redis.delete(redis_key)
                raise OTPMaxAttemptsError()

            ttl = await self.redis.ttl(redis_key)
            if ttl > 0:
                await self.redis.setex(redis_key, ttl, json.dumps(session))

            raise InvalidOTPError()

        # OTP accepted — promote session
        session["otp_verified"] = True
        ttl = await self.redis.ttl(redis_key)
        await self.redis.setex(redis_key, max(ttl, 1), json.dumps(session))

        log.info(
            "password_reset.otp_verified",
            user_id=session.get("user_id"),
        )

        return {
            "reset_token": reset_token,
            "message":     "OTP verified. You may now set a new password.",
        }

    async def complete_password_reset(
        self,
        reset_token:  str,
        new_password: str,
    ) -> None:
        """
        Step 3 — set a new password after OTP verification.

        Reads the promoted Redis session (otp_verified must be True).
        On success:
          · Sets new Argon2id-hashed password.
          · Invalidates all existing DB reset tokens.
          · Deletes the Redis session (single-use).
          · Commits and publishes user.password_reset.

        NOTE: Active refresh tokens (sessions on other devices) are not
        revoked here because a secondary index from user_id → refresh tokens
        does not exist.  To add session revocation, store a secondary key
        user_refresh:<user_id>:<token> at token issuance time.
        """
        assert self.redis is not None

        redis_key = f"{_PWD_RESET_PREFIX}{reset_token}"
        raw       = await self.redis.get(redis_key)

        if not raw:
            raise InvalidTokenError()

        session = json.loads(raw)

        if not session.get("otp_verified"):
            raise InvalidTokenError(
                "OTP has not been verified. Complete Step 2 first."
            )

        user_id = uuid.UUID(session["user_id"])
        user    = await self.user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError()

        ok, reason = validate_password_strength(new_password)
        if not ok:
            raise WeakPasswordError(reason)

        new_hash = hash_password(new_password)
        await self.user_repo.set_password(user_id, new_hash)
        await self.pw_reset_repo.invalidate_all_for_user(user_id)

        # Consume the Redis session immediately (prevent replay)
        await self.redis.delete(redis_key)

        await self.db.commit()

        # Reload for event payload
        user = await self.user_repo.get_by_id(user_id)
        log.info("user.password_reset", user_id=str(user_id))
        await self.publisher.user_password_reset(user)

    # ── DB-token reset path (email link flow) ─────────────────────────────────

    async def reset_password_with_token(
        self,
        user_id:   uuid.UUID,
        raw_token: str,
        new_pass:  str,
    ) -> User:
        """
        Complete a password-reset flow using a valid DB reset token.

        Used by the email-link flow where the raw token is embedded in a
        URL and submitted to the API.  The token is hashed and looked up
        in password_reset_tokens.

        Raises InvalidTokenError / TokenExpiredError for bad tokens.
        """
        token_hash  = hash_token(raw_token)
        reset_token = await self.pw_reset_repo.get_valid_by_hash(token_hash)
        if not reset_token or str(reset_token.user_id) != str(user_id):
            raise InvalidTokenError()

        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError()

        ok, reason = validate_password_strength(new_pass)
        if not ok:
            raise WeakPasswordError(reason)

        new_hash = hash_password(new_pass)
        await self.user_repo.set_password(user_id, new_hash)
        await self.pw_reset_repo.consume(reset_token)
        await self.pw_reset_repo.invalidate_all_for_user(user_id)
        await self.db.commit()

        user = await self.user_repo.get_by_id(user_id)
        log.info("user.password_reset", user_id=str(user_id))
        await self.publisher.user_password_reset(user)
        return user

    # ── Profile management ────────────────────────────────────────────────────

    async def update_profile(self, user: User, updates: dict) -> User:
        """
        Update mutable profile fields: display_name, full_name, avatar_url,
        country_code, language.  Ignores unknown fields.
        """
        allowed = {"display_name", "full_name", "avatar_url", "country_code", "language"}
        changed_fields = [k for k in updates if k in allowed]
        if not changed_fields:
            return user

        await self.user_repo.update_profile(
            user.id, **{k: updates[k] for k in changed_fields}
        )
        await self.db.commit()

        user = await self.user_repo.get_by_id(user.id)
        log.info("user.profile_updated", user_id=str(user.id), fields=changed_fields)
        await self.publisher.user_profile_updated(user, changed_fields)
        return user

    # ── Account status changes (admin) ────────────────────────────────────────

    async def suspend(self, user_id: uuid.UUID, reason: Optional[str] = None) -> User:
        user = await self._get_or_404(user_id)
        await self.user_repo.set_status(user_id, AccountStatus.SUSPENDED)
        await self.db.commit()
        user = await self.user_repo.get_by_id(user_id)
        log.info("user.suspended", user_id=str(user_id), reason=reason)
        await self.publisher.user_status_changed(user, UserEvents.SUSPENDED, reason=reason)
        return user

    async def ban(self, user_id: uuid.UUID, reason: Optional[str] = None) -> User:
        user = await self._get_or_404(user_id)
        await self.user_repo.set_status(user_id, AccountStatus.BANNED)
        await self.db.commit()
        user = await self.user_repo.get_by_id(user_id)
        log.info("user.banned", user_id=str(user_id), reason=reason)
        await self.publisher.user_status_changed(user, UserEvents.BANNED, reason=reason)
        return user

    async def reactivate(self, user_id: uuid.UUID, reason: Optional[str] = None) -> User:
        user = await self._get_or_404(user_id)
        await self.user_repo.set_status(user_id, AccountStatus.ACTIVE)
        await self.db.commit()
        user = await self.user_repo.get_by_id(user_id)
        log.info("user.reactivated", user_id=str(user_id))
        await self.publisher.user_status_changed(user, UserEvents.REACTIVATED, reason=reason)
        return user

    async def deactivate(self, user: User, reason: Optional[str] = None) -> None:
        await self.user_repo.soft_delete(user.id)
        await self.db.commit()
        log.info("user.deactivated", user_id=str(user.id))
        await self.publisher.user_status_changed(user, UserEvents.DEACTIVATED, reason=reason)

    # ── OAuth linking ─────────────────────────────────────────────────────────

    async def link_oauth(self, user: User, provider: str, provider_id: str) -> User:
        await self.user_repo.link_oauth_provider(user.id, provider, provider_id)
        await self.db.commit()
        user = await self.user_repo.get_by_id(user.id)
        log.info("user.oauth_linked", user_id=str(user.id), provider=provider)
        await self.publisher.user_oauth_linked(user, provider)
        return user

    # ── ID verification callback ──────────────────────────────────────────────

    async def on_id_verified(self, user: User) -> User:
        await self.user_repo.mark_id_verified(user.id)
        await self.db.commit()
        user = await self.user_repo.get_by_id(user.id)
        log.info("user.id_verified", user_id=str(user.id))
        await self.publisher.user_id_verified(user)
        return user

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _get_or_404(self, user_id: uuid.UUID) -> User:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError()
        return user


# ── Privacy helpers ───────────────────────────────────────────────────────────

def _mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    visible = local[:2] if len(local) > 2 else local[:1]
    return f"{visible}***@{domain}"


def _mask_phone(phone: str) -> str:
    if len(phone) <= 7:
        return phone[:3] + "***"
    return phone[:4] + "***" + phone[-4:]

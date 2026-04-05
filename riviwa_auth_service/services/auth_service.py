"""
services/auth_service.py
═══════════════════════════════════════════════════════════════════════════════
Authentication operations: login (2-step OTP), logout, token refresh,
dashboard switch.

Login flow
──────────
  Step 1  login()           identifier + password → OTP dispatched
                            Returns login_token (Redis TTL 5 min)
  Step 2  verify_login_otp()  login_token + otp_code → TokenResponse

Kafka events published
──────────────────────
  auth.login_success
  auth.login_failed
  auth.login_locked
  auth.logout
  auth.token_refreshed
  auth.dashboard_switched
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import structlog
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.exceptions import (
    AccountBannedError,
    AccountDeactivatedError,
    AccountLockedError,
    AccountSuspendedError,
    InvalidCredentialsError,
    InvalidOTPError,
    OTPExpiredError,
    OTPMaxAttemptsError,
    OrgMembershipRequiredError,
    RefreshTokenInvalidError,
)
from core.notifications import get_provider_for_channel
from core.security import (
    create_access_token,
    generate_refresh_token,
    generate_session_token,
    hash_password,
    needs_rehash,
    verify_password,
)
from events.publisher import EventPublisher
from models.user import AccountStatus, User
from repositories.organisation_repository import OrganisationRepository
from repositories.user_repository import UserRepository

log = structlog.get_logger(__name__)

# ── Redis key prefixes ────────────────────────────────────────────────────────
_REFRESH_PREFIX  = "refresh:"
_JTI_DENY_PREFIX = "jti_deny:"
_LOGIN_PREFIX    = "login:"       # login:<login_token> → JSON session

# ── Login OTP session TTL ─────────────────────────────────────────────────────
_LOGIN_OTP_TTL_SECONDS = getattr(settings, "OTP_LOGIN_TTL_SECONDS", 300)   # 5 min
_OTP_MAX_ATTEMPTS      = getattr(settings, "OTP_MAX_ATTEMPTS", 5)

# ── Lockout policy ────────────────────────────────────────────────────────────
_MAX_FAILED_ATTEMPTS = getattr(settings, "MAX_LOGIN_ATTEMPTS", 5)
_LOCKOUT_MINUTES     = getattr(settings, "LOCKOUT_DURATION_MINUTES", 30)

# ── Refresh token TTL ─────────────────────────────────────────────────────────
_REFRESH_EXPIRE_DAYS = getattr(settings, "REFRESH_TOKEN_EXPIRE_DAYS", 7)


class AuthService:

    def __init__(
        self,
        db:        AsyncSession,
        redis:     Redis,
        publisher: EventPublisher,
    ) -> None:
        self.db        = db
        self.redis     = redis
        self.publisher = publisher
        self.user_repo = UserRepository(db)
        self.org_repo  = OrganisationRepository(db)

    # ── Login — Step 1: credentials ───────────────────────────────────────────

    async def login(
        self,
        identifier: str,
        password:   str,
        ip_address: str,
        user_agent: Optional[str] = None,
    ) -> dict:
        """
        Step 1 of the two-step login flow.

        Verifies identifier + password, then dispatches a 6-digit OTP
        via the channel that matches the identifier type (email → email,
        phone → SMS).

        Returns a dict matching LoginCredentialsResponse:
            {
                "login_token":        str,   (Redis key, TTL 5 min)
                "otp_channel":        str,   ("email" | "sms")
                "otp_destination":    str,   (masked destination)
                "expires_in_seconds": int,   (300)
            }

        Raises:
            InvalidCredentialsError   — wrong identifier or wrong password
                                        (intentionally generic, prevents enumeration)
            AccountLockedError        — too many failed attempts
            AccountSuspendedError     — account manually suspended
            AccountBannedError        — account banned
            AccountDeactivatedError   — account soft-deleted
        """
        user = await self.user_repo.get_by_identifier(identifier)

        if not user or not user.hashed_password:
            await self.publisher.auth_login_failed(
                identifier, ip_address, "unknown_identifier"
            )
            raise InvalidCredentialsError()

        # Check lockout BEFORE verifying password (saves Argon2id time on brute-force)
        if user.is_locked():
            await self.publisher.auth_login_locked(user.id, ip_address)
            raise AccountLockedError()

        if not verify_password(password, user.hashed_password):
            await self._handle_failed_attempt(user, ip_address)
            await self.publisher.auth_login_failed(
                identifier, ip_address, "wrong_password"
            )
            raise InvalidCredentialsError()

        # Account status gate
        _status_exc = {
            AccountStatus.SUSPENDED:   AccountSuspendedError,
            AccountStatus.BANNED:      AccountBannedError,
            AccountStatus.DEACTIVATED: AccountDeactivatedError,
        }
        if user.status in _status_exc:
            raise _status_exc[user.status]()

        # Transparent rehash if Argon2id parameters have changed
        if needs_rehash(user.hashed_password):
            new_hash = hash_password(password)
            await self.user_repo.set_password(user.id, new_hash)
            log.debug("auth.password_rehashed", user_id=str(user.id))

        await self.db.commit()

        # ── Determine channel and recipient ───────────────────────────────
        if identifier.startswith("+") and user.phone_number:
            channel     = "sms"
            to          = user.phone_number
            destination = _mask_phone(user.phone_number)
        else:
            channel     = "email"
            to          = user.email
            destination = _mask_email(user.email)

        login_token = generate_session_token()

        # ── Dispatch OTP via configured provider ──────────────────────────
        provider         = get_provider_for_channel(channel)
        provider_payload = await provider.send_otp(
            to=to,
            channel=channel,
            display_name=user.display_name,
            purpose="login",
        )

        # ── Store session in Redis ─────────────────────────────────────────
        # provider_payload shape depends on provider:
        #   twilio_verify → { provider, to, channel, verification_sid }
        #   twilio_sms    → { provider, to, otp_hash, message_sid }
        #   smtp / stub   → { provider, to, otp_hash }
        session_data = {
            "user_id":    str(user.id),
            "attempts":   0,
            "channel":    channel,
            "ip_address": ip_address,
            "created_at": datetime.now(timezone.utc).isoformat(),
            **provider_payload,
        }
        await self.redis.setex(
            f"{_LOGIN_PREFIX}{login_token}",
            _LOGIN_OTP_TTL_SECONDS,
            json.dumps(session_data),
        )

        log.info(
            "auth.otp_dispatched",
            user_id=str(user.id),
            channel=channel,
            ip=ip_address,
            provider=provider_payload.get("provider"),
        )

        return {
            "login_token":        login_token,
            "otp_channel":        channel,
            "otp_destination":    destination,
            "expires_in_seconds": _LOGIN_OTP_TTL_SECONDS,
        }

    # ── Login — Step 2: OTP verification ─────────────────────────────────────

    async def verify_login_otp(
        self,
        login_token: str,
        otp_code:    str,
        ip_address:  str,
    ) -> dict:
        """
        Step 2 of the two-step login flow.

        Verifies the 6-digit OTP submitted by the user, then:
          · Resets failed_login_attempts to 0.
          · Records last_login_at / last_login_ip.
          · Issues a JWT access token + opaque refresh token.
          · Deletes the login session from Redis (single-use).

        Returns a dict matching TokenResponse:
            { access_token, refresh_token, token_type, expires_in }

        Raises:
            InvalidOTPError      — wrong code
            OTPExpiredError      — session not found in Redis (TTL elapsed)
            OTPMaxAttemptsError  — 5 consecutive wrong codes; session deleted
        """
        redis_key = f"{_LOGIN_PREFIX}{login_token}"
        raw       = await self.redis.get(redis_key)

        if not raw:
            raise OTPExpiredError()

        session  = json.loads(raw)
        attempts = session.get("attempts", 0)

        # ── Max-attempts guard ────────────────────────────────────────────
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

            # Update attempt counter (preserve remaining TTL)
            ttl = await self.redis.ttl(redis_key)
            if ttl > 0:
                await self.redis.setex(redis_key, ttl, json.dumps(session))

            raise InvalidOTPError()

        # ── OTP accepted — single-use consumption ─────────────────────────
        await self.redis.delete(redis_key)

        user_id = uuid.UUID(session["user_id"])

        # Load user with platform_roles eagerly to avoid lazy-load MissingGreenlet
        user = await self.user_repo.get_by_id_with_roles(user_id)
        if not user or user.status != AccountStatus.ACTIVE:
            raise InvalidCredentialsError()

        # Record successful login
        await self.user_repo.record_login(user_id, ip_address)
        await self.db.commit()

        # Build JWT
        org_id, org_role, platform_role = await self._resolve_jwt_context(user)
        token, jti, expires_in = create_access_token(
            user_id=user_id,
            org_id=org_id,
            org_role=org_role,
            platform_role=platform_role,
        )
        refresh = generate_refresh_token()
        await self._store_refresh_token(refresh, user_id)

        log.info(
            "auth.login_success",
            user_id=str(user_id),
            ip=ip_address,
        )
        await self.publisher.auth_login_success(user_id, ip_address)

        return {
            "access_token":  token,
            "refresh_token": refresh,
            "token_type":    "bearer",
            "expires_in":    expires_in,
        }

    # ── Logout ────────────────────────────────────────────────────────────────

    async def logout(
        self,
        user_id:       uuid.UUID,
        jti:           str,
        refresh_token: Optional[str] = None,
        access_token_remaining_seconds: int = 0,
    ) -> None:
        """
        Invalidate the current session:
          · Add JTI to deny-list (TTL = remaining access token seconds).
          · Delete the refresh token from Redis.
          · Publish auth.logout.
        """
        ttl = max(access_token_remaining_seconds, 60)
        await self.redis.setex(f"{_JTI_DENY_PREFIX}{jti}", ttl, "1")

        if refresh_token:
            await self.redis.delete(f"{_REFRESH_PREFIX}{refresh_token}")

        log.info("auth.logout", user_id=str(user_id), jti=jti)
        await self.publisher.auth_logout(user_id=user_id, jti=jti)

    # ── Token refresh ─────────────────────────────────────────────────────────

    async def refresh_tokens(self, refresh_token: str, ip_address: str) -> dict:
        """
        Rotate the refresh token and issue a new access token.

        Raises RefreshTokenInvalidError for missing or expired tokens.
        """
        redis_key   = f"{_REFRESH_PREFIX}{refresh_token}"
        user_id_str = await self.redis.get(redis_key)
        if not user_id_str:
            raise RefreshTokenInvalidError()

        user_id = uuid.UUID(user_id_str)
        user    = await self.user_repo.get_by_id_with_roles(user_id)
        if not user or user.status != AccountStatus.ACTIVE:
            await self.redis.delete(redis_key)
            raise RefreshTokenInvalidError()

        # Rotate — delete old, store new
        await self.redis.delete(redis_key)
        new_refresh = generate_refresh_token()
        await self._store_refresh_token(new_refresh, user_id)

        org_id, org_role, platform_role = await self._resolve_jwt_context(user)
        token, jti, expires_in = create_access_token(
            user_id=user.id,
            org_id=org_id,
            org_role=org_role,
            platform_role=platform_role,
        )

        log.info("auth.token_refreshed", user_id=str(user_id), ip=ip_address)
        await self.publisher.auth_token_refreshed(
            user_id=user_id, ip_address=ip_address
        )

        return {
            "access_token":  token,
            "refresh_token": new_refresh,
            "token_type":    "bearer",
            "expires_in":    expires_in,
        }

    # ── Dashboard switch ──────────────────────────────────────────────────────

    async def switch_org(self, user: User, org_id: Optional[uuid.UUID]) -> dict:
        """
        Switch the user's active org dashboard and reissue a new JWT pair.
        """
        org_role:      Optional[str] = None
        platform_role = self._get_platform_role(user)

        if org_id is not None:
            member = await self.org_repo.get_active_member(org_id, user.id)
            if not member:
                raise OrgMembershipRequiredError()
            org_role = member.org_role.value

        await self.user_repo.update_active_org(user.id, org_id)
        await self.db.commit()

        token, jti, expires_in = create_access_token(
            user_id=user.id,
            org_id=org_id,
            org_role=org_role,
            platform_role=platform_role,
        )
        new_refresh = generate_refresh_token()
        await self._store_refresh_token(new_refresh, user.id)

        log.info(
            "auth.dashboard_switched",
            user_id=str(user.id),
            org_id=str(org_id) if org_id else "personal",
        )
        await self.publisher.auth_dashboard_switched(user.id, org_id)

        return {
            "access_token":  token,
            "refresh_token": new_refresh,
            "token_type":    "bearer",
            "expires_in":    expires_in,
            "org_id":        str(org_id) if org_id else None,
            "org_role":      org_role,
            "platform_role": platform_role,
        }

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _handle_failed_attempt(self, user: User, ip_address: str) -> None:
        new_count  = (user.failed_login_attempts or 0) + 1
        lock_until = None
        if new_count >= _MAX_FAILED_ATTEMPTS:
            lock_until = datetime.now(timezone.utc) + timedelta(
                minutes=_LOCKOUT_MINUTES
            )
            log.warning(
                "auth.account_locked",
                user_id=str(user.id),
                attempts=new_count,
            )
            await self.publisher.auth_login_locked(user.id, ip_address)

        await self.user_repo.increment_failed_login(user.id, lock_until=lock_until)
        await self.db.commit()

    async def _resolve_jwt_context(
        self, user: User
    ) -> tuple[Optional[uuid.UUID], Optional[str], Optional[str]]:
        org_id        = user.active_org_id
        org_role      = None
        platform_role = self._get_platform_role(user)

        if org_id:
            member = await self.org_repo.get_active_member(org_id, user.id)
            if member:
                org_role = member.org_role.value
            else:
                await self.user_repo.update_active_org(user.id, None)
                org_id = None

        return org_id, org_role, platform_role

    def _get_platform_role(self, user: User) -> Optional[str]:
        names    = user.get_platform_role_names()
        priority = ["super_admin", "admin", "moderator"]
        for role in priority:
            if role in names:
                return role
        return names[0] if names else None

    async def _store_refresh_token(
        self, refresh_token: str, user_id: uuid.UUID
    ) -> None:
        ttl = _REFRESH_EXPIRE_DAYS * 86400
        await self.redis.setex(
            f"{_REFRESH_PREFIX}{refresh_token}",
            ttl,
            str(user_id),
        )


# ── Privacy helpers (module-level, reusable) ──────────────────────────────────

def _mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    visible = local[:2] if len(local) > 2 else local[:1]
    return f"{visible}***@{domain}"


def _mask_phone(phone: str) -> str:
    if len(phone) <= 7:
        return phone[:3] + "***"
    return phone[:4] + "***" + phone[-4:]

"""
repositories/user_repository.py
═══════════════════════════════════════════════════════════════════════════════
All DB operations for the users table.

Design rules
────────────
  · Pure DB access — zero business logic.
  · Returns None for not-found (service layer raises exceptions).
  · Uses flush() only — commit is owned by the service layer or the
    get_async_session() dependency in db/session.py.
  · Targeted UPDATE statements via SQLAlchemy update() for performance
    instead of loading the whole row, mutating, then flushing.
  · All lookups are by indexed columns.
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog
from sqlalchemy import select, update
from sqlalchemy.exc import DataError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.user import AccountStatus, User
from models.user_role import UserRole

log = structlog.get_logger(__name__)


class UserRepository:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Lookups ───────────────────────────────────────────────────────────────

    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_with_roles(self, user_id: uuid.UUID) -> Optional[User]:
        """
        Load the User with platform_roles → role eagerly resolved.

        Use this instead of get_by_id() whenever the caller will access
        user.platform_roles (e.g. _resolve_jwt_context, _get_platform_role).
        Accessing that relationship without eager loading triggers a synchronous
        lazy-load which raises MissingGreenlet on asyncpg.

        selectinload fires one extra async SELECT … WHERE user_id IN (…)
        and is the recommended pattern for async SQLAlchemy on collections.
        """
        result = await self.db.execute(
            select(User)
            .options(
                selectinload(User.platform_roles).selectinload(UserRole.role)
            )
            .where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(User.email == email.lower().strip())
        )
        return result.scalar_one_or_none()

    async def get_by_email_normalized(self, email_normalized: str) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(User.email_normalized == email_normalized)
        )
        return result.scalar_one_or_none()

    async def get_by_phone(self, phone_number: str) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(User.phone_number == phone_number)
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def get_by_oauth(
        self,
        provider:    str,
        provider_id: str,
    ) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(
                User.oauth_provider    == provider,
                User.oauth_provider_id == provider_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_identifier(self, identifier: str) -> Optional[User]:
        """
        Lookup by either email or E.164 phone number.
        Used by login services where the user supplies either form.
        """
        # Try email first (most common)
        user = await self.get_by_email(identifier)
        if user:
            return user
        # Try phone
        if identifier.startswith("+"):
            user = await self.get_by_phone(identifier)
        return user

    # ── Existence checks  (lighter than full-row loads) ───────────────────────

    async def email_exists(self, email: str) -> bool:
        result = await self.db.execute(
            select(User.id).where(User.email == email.lower().strip())
        )
        return result.scalar_one_or_none() is not None

    async def email_normalized_exists(self, email_normalized: str) -> bool:
        result = await self.db.execute(
            select(User.id).where(User.email_normalized == email_normalized)
        )
        return result.scalar_one_or_none() is not None

    async def phone_exists(self, phone_number: str) -> bool:
        result = await self.db.execute(
            select(User.id).where(User.phone_number == phone_number)
        )
        return result.scalar_one_or_none() is not None

    async def username_exists(self, username: str) -> bool:
        result = await self.db.execute(
            select(User.id).where(User.username == username)
        )
        return result.scalar_one_or_none() is not None

    # ── Create ────────────────────────────────────────────────────────────────

    async def create(
        self,
        *,
        username:         str,
        email:            Optional[str]           = None,   # None for phone-only users
        email_normalized: Optional[str]           = None,   # None for phone-only users
        hashed_password:  Optional[str]           = None,
        phone_number:     Optional[str]           = None,
        display_name:     Optional[str]           = None,
        full_name:        Optional[str]           = None,
        country_code:     Optional[str]           = None,
        language:         str                     = "en",
        status:           AccountStatus           = AccountStatus.PENDING_EMAIL,
        fraud_score:      int                     = 0,
        oauth_provider:   Optional[str]           = None,
        oauth_provider_id: Optional[str]          = None,
        is_email_verified: bool                   = False,
        phone_verified:   bool                    = False,
    ) -> User:
        """
        INSERT a new User row and flush to the session (no commit).

        Caller is responsible for committing (or allowing the session
        dependency to commit at request teardown).
        """
        user = User(
            username=username,
            email=email,
            email_normalized=email_normalized,
            hashed_password=hashed_password,
            phone_number=phone_number,
            display_name=display_name,
            full_name=full_name,
            country_code=country_code,
            language=language,
            status=status,
            fraud_score=fraud_score,
            oauth_provider=oauth_provider,
            oauth_provider_id=oauth_provider_id,
            is_email_verified=is_email_verified,
            phone_verified=phone_verified,
        )
        self.db.add(user)
        try:
            await self.db.flush()
            await self.db.refresh(user)
        except DataError as exc:
            # Catch DB-level constraint violations (e.g. value too long for
            # VARCHAR(2) country_code) and surface as a clean 422 instead of 500.
            original = str(exc.orig) if exc.orig else str(exc)
            log.warning("user_repository.create.data_error", error=original)
            # Import inline to avoid circular import at module level.
            from core.exceptions import ValidationError as AppValidationError
            if "too long" in original.lower() or "string data right truncation" in original.lower():
                raise AppValidationError(
                    "One or more fields exceed the maximum allowed length. "
                    "Check country_code (must be 2 letters) and other short fields."
                ) from exc
            raise AppValidationError(
                "The submitted data failed a database constraint. "
                "Please check your input and try again."
            ) from exc
        log.debug("user.created", user_id=str(user.id), status=status.value)
        return user

    # ── Targeted updates ──────────────────────────────────────────────────────

    async def set_status(
        self,
        user_id: uuid.UUID,
        status:  AccountStatus,
    ) -> None:
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(status=status)
        )
        await self.db.flush()

    async def set_password(
        self,
        user_id:         uuid.UUID,
        hashed_password: str,
    ) -> None:
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(hashed_password=hashed_password)
        )
        await self.db.flush()

    async def mark_email_verified(self, user_id: uuid.UUID) -> None:
        now = datetime.now(timezone.utc)
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                is_email_verified=True,
                email_verified_at=now,
                status=AccountStatus.ACTIVE,
            )
        )
        await self.db.flush()

    async def mark_phone_verified(self, user_id: uuid.UUID) -> None:
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(phone_verified=True)
        )
        await self.db.flush()

    async def mark_id_verified(self, user_id: uuid.UUID) -> None:
        """
        Set id_verified=True, id_verified_at=now, and transition
        PENDING_ID → ACTIVE.  Called by IDVerificationService on approval.
        """
        now = datetime.now(timezone.utc)
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                id_verified=True,
                id_verified_at=now,
                status=AccountStatus.ACTIVE,
            )
        )
        await self.db.flush()

    async def record_login(
        self,
        user_id:    uuid.UUID,
        ip_address: str,
    ) -> None:
        """
        Record a successful login:
          · Update last_login_at and last_login_ip.
          · Reset failed_login_attempts to 0.
          · Clear locked_until (unlock the account).
        """
        now = datetime.now(timezone.utc)
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                last_login_at=now,
                last_login_ip=ip_address,
                failed_login_attempts=0,
                locked_until=None,
            )
        )
        await self.db.flush()

    async def increment_failed_login(
        self,
        user_id:      uuid.UUID,
        lock_until:   Optional[datetime] = None,
    ) -> None:
        """
        Increment failed_login_attempts.
        When lock_until is provided, also set locked_until (account lockout).
        """
        values: dict = {}
        # Use SQL expression for atomic increment
        from sqlalchemy import func as sqlfunc
        result = await self.db.execute(
            select(User.failed_login_attempts).where(User.id == user_id)
        )
        current = result.scalar_one_or_none() or 0
        values["failed_login_attempts"] = current + 1
        if lock_until is not None:
            values["locked_until"] = lock_until
        await self.db.execute(
            update(User).where(User.id == user_id).values(**values)
        )
        await self.db.flush()

    async def update_active_org(
        self,
        user_id: uuid.UUID,
        org_id:  Optional[uuid.UUID],
    ) -> None:
        """
        Set User.active_org_id.
        NULL → personal/consumer view.  UUID → org dashboard.
        """
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(active_org_id=org_id)
        )
        await self.db.flush()

    async def link_oauth_provider(
        self,
        user_id:     uuid.UUID,
        provider:    str,
        provider_id: str,
    ) -> None:
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                oauth_provider=provider,
                oauth_provider_id=provider_id,
            )
        )
        await self.db.flush()

    async def update_profile(
        self,
        user_id: uuid.UUID,
        **fields,
    ) -> None:
        """
        Generic profile field update.
        Accepted fields: display_name, full_name, avatar_url, country_code, language.
        Any other keys are silently dropped for safety.
        """
        allowed = {"display_name", "full_name", "avatar_url", "country_code", "language"}
        safe_fields = {k: v for k, v in fields.items() if k in allowed}
        if not safe_fields:
            return
        await self.db.execute(
            update(User).where(User.id == user_id).values(**safe_fields)
        )
        await self.db.flush()

    async def update_fraud_score(
        self,
        user_id:     uuid.UUID,
        fraud_score: int,
    ) -> None:
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(fraud_score=fraud_score)
        )
        await self.db.flush()

    async def soft_delete(self, user_id: uuid.UUID) -> None:
        """
        Soft-delete: set status=DEACTIVATED and deleted_at=now().
        Hard data remains in the DB for compliance / fraud history.
        """
        now = datetime.now(timezone.utc)
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(status=AccountStatus.DEACTIVATED, deleted_at=now)
        )
        await self.db.flush()
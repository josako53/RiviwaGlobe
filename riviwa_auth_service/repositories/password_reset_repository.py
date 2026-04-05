"""
repositories/password_reset_repository.py
═══════════════════════════════════════════════════════════════════════════════
DB operations for the password_reset_tokens table.

Security design (mirrors the model docstring)
──────────────────────────────────────────────
  · Only the SHA-256 hash of the raw token is stored.
  · The raw token is sent to the user and never persisted.
  · A second use of the same token is blocked by the used_at IS NOT NULL check
    inside PasswordResetToken.is_valid().
  · All previous tokens for a user are invalidated before a new one is issued.
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog
from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.password_reset import PasswordResetToken

log = structlog.get_logger(__name__)


class PasswordResetRepository:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_token(
        self,
        user_id:         uuid.UUID,
        token_hash:      str,
        expires_at:      datetime,
        delivery_method: str = "email",   # "email" | "phone"
    ) -> PasswordResetToken:
        """
        Invalidate all existing tokens for this user, then INSERT a new one.
        Two steps are atomic within the same transaction.
        """
        # Step 1: invalidate previous tokens (mark as used right now)
        now = datetime.now(timezone.utc)
        await self.db.execute(
            update(PasswordResetToken)
            .where(
                and_(
                    PasswordResetToken.user_id  == user_id,
                    PasswordResetToken.used_at  == None,   # noqa: E711
                )
            )
            .values(used_at=now)
        )

        # Step 2: insert fresh token
        token = PasswordResetToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            delivery_method=delivery_method,
        )
        self.db.add(token)
        await self.db.flush()
        await self.db.refresh(token)
        log.debug("password_reset.token_created", user_id=str(user_id))
        return token

    async def get_valid_by_hash(
        self,
        token_hash: str,
    ) -> Optional[PasswordResetToken]:
        """
        Look up a token by its SHA-256 hash.
        Returns None if not found or if is_valid() returns False (used / expired).
        """
        result = await self.db.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.token_hash == token_hash
            )
        )
        token = result.scalar_one_or_none()
        if token and token.is_valid():
            return token
        return None

    async def consume(self, token: PasswordResetToken) -> None:
        """
        Mark a token as consumed (used_at=now).
        Call immediately after verifying a valid token to prevent replay.
        """
        token.used_at = datetime.now(timezone.utc)
        await self.db.flush()
        log.debug("password_reset.token_consumed", token_id=str(token.id))

    async def invalidate_all_for_user(self, user_id: uuid.UUID) -> None:
        """
        Bulk-invalidate all unconsumed tokens for a user.
        Called when a password is changed via any mechanism (reset, change form).
        """
        now = datetime.now(timezone.utc)
        await self.db.execute(
            update(PasswordResetToken)
            .where(
                and_(
                    PasswordResetToken.user_id == user_id,
                    PasswordResetToken.used_at == None,    # noqa: E711
                )
            )
            .values(used_at=now)
        )
        await self.db.flush()

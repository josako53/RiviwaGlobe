"""db/session.py — Two async engine/session factories for analytics_service."""
from __future__ import annotations

from typing import AsyncGenerator

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.config import settings

log = structlog.get_logger(__name__)

# ── Analytics DB (read + write) ───────────────────────────────────────────────
analytics_engine = create_async_engine(
    settings.ASYNC_ANALYTICS_DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
)

AnalyticsSessionLocal = async_sessionmaker(
    bind=analytics_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_analytics_session() -> AsyncGenerator[AsyncSession, None]:
    async with AnalyticsSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ── Feedback DB (read-only — cross-service analytics) ─────────────────────────
# execution_options(no_autoflush=True) + connect_args read-only role enforced at DB level.
# The asyncpg connection is opened in read-only transaction mode where possible.
feedback_ro_engine = create_async_engine(
    settings.ASYNC_FEEDBACK_DATABASE_URL,
    echo=False,
    pool_size=5,
    max_overflow=10,
    execution_options={"readonly": True},
)

FeedbackROSessionLocal = async_sessionmaker(
    bind=feedback_ro_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_feedback_session() -> AsyncGenerator[AsyncSession, None]:
    async with FeedbackROSessionLocal() as session:
        try:
            yield session
            # Never commit on the read-only session — just rollback to release locks.
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.rollback()
            await session.close()

"""
db/session.py
═══════════════════════════════════════════════════════════════════════════════
Async database session factory for stakeholder_service.
Mirrors the exact pattern from auth_service/db/session.py.
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

from typing import AsyncGenerator

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.config import settings

log = structlog.get_logger(__name__)

engine = create_async_engine(
    settings.ASYNC_DATABASE_URL,
    echo=getattr(settings, "SQL_ECHO", False),
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield an AsyncSession for the current request.
    Commits on clean exit, rolls back on exception, always closes.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

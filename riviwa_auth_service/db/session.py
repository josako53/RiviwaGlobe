"""
db/session.py
═══════════════════════════════════════════════════════════════════════════════
Async database session factory and Redis connection pool.

Both are singletons initialised once at startup and shared across requests.
The session factory yields one AsyncSession per request with auto-commit /
auto-rollback / auto-close behaviour.
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

from typing import AsyncGenerator, Optional

import structlog
from redis.asyncio import Redis, from_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.config import settings

log = structlog.get_logger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# SQLAlchemy async engine + session factory
# ─────────────────────────────────────────────────────────────────────────────

engine = create_async_engine(
    settings.ASYNC_DATABASE_URL,
    echo=getattr(settings, "SQL_ECHO", False),
    # pool_pre_ping is intentionally omitted for asyncpg.
    # asyncpg uses greenlets internally; SQLAlchemy's synchronous ping shim
    # raises MissingGreenlet when it tries to await outside a greenlet context.
    # asyncpg already surfaces dead connections as exceptions on first use,
    # so the pre-ping provides no additional safety here.
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,      # ORM objects stay usable after commit
    autocommit=False,
    autoflush=False,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield an AsyncSession for the current request.

    Commits on clean exit. Rolls back on any unhandled exception.
    Session is always closed in the finally block.

    Used as a FastAPI dependency via get_db() in core/dependencies.py.
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


# ─────────────────────────────────────────────────────────────────────────────
# Redis pool
# ─────────────────────────────────────────────────────────────────────────────

_redis_client: Optional[Redis] = None


async def init_redis() -> None:
    """
    Create the Redis connection pool.
    Call once in the FastAPI lifespan startup handler.
    """
    global _redis_client
    _redis_client = from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
    )
    # Verify connectivity
    await _redis_client.ping()
    log.info("redis.connected", url=settings.REDIS_URL)


async def close_redis() -> None:
    """Close the Redis pool.  Call in the lifespan shutdown handler."""
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None
        log.info("redis.closed")


async def get_redis_client() -> Redis:
    """
    Return the shared Redis client.
    Raises RuntimeError if init_redis() was not called at startup.
    """
    if _redis_client is None:
        raise RuntimeError("Redis not initialised — call init_redis() at startup.")
    return _redis_client
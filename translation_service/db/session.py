# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  translation_service  |  Port: 8050  |  DB: translation_db (5438)
# FILE     :  db/session.py
# ───────────────────────────────────────────────────────────────────────────
"""db/session.py — Async SQLAlchemy session factory."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.config import settings

engine = create_async_engine(
    settings.ASYNC_DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=settings.DEBUG,
)

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

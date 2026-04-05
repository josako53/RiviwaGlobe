# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  translation_service  |  Port: 8050  |  DB: translation_db (5438)
# FILE     :  core/dependencies.py
# ───────────────────────────────────────────────────────────────────────────
"""core/dependencies.py — FastAPI dependency providers."""
from __future__ import annotations

from typing import Annotated, AsyncGenerator

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from db.session import AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


DbDep = Annotated[AsyncSession, Depends(get_db)]


def require_service_key(
    x_service_key: str = Header(..., alias="X-Service-Key"),
) -> None:
    """
    Guards internal endpoints called service-to-service.
    Every other Riviwa service (auth, feedback, notification, etc.) uses this
    header when asking for a user's language or posting a detected language.
    """
    if x_service_key != settings.INTERNAL_SERVICE_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid service key.",
        )


ServiceKeyDep = Depends(require_service_key)

"""core/dependencies.py — Shared FastAPI dependencies."""
from __future__ import annotations

from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from db.session import AsyncSessionLocal


# ── Database session ──────────────────────────────────────────────────────────

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

DbDep = Annotated[AsyncSession, Depends(get_db)]


# ── JWT verification ─────────────────────────────────────────────────────────

def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            settings.AUTH_SECRET_KEY,
            algorithms=[settings.AUTH_ALGORITHM],
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "UNAUTHORISED", "message": "JWT verification failed."},
        )


async def get_current_user(
    authorization: Annotated[Optional[str], Header()] = None,
) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "UNAUTHORISED", "message": "Missing bearer token."},
        )
    return _decode_token(authorization[7:])


CurrentUser = Annotated[dict, Depends(get_current_user)]


# ── Internal service key guard ────────────────────────────────────────────────

async def require_internal_key(
    x_service_key: Annotated[Optional[str], Header(alias="X-Service-Key")] = None,
) -> None:
    if x_service_key != settings.INTERNAL_SERVICE_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "FORBIDDEN", "message": "Invalid service key."},
        )

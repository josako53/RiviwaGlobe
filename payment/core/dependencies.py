"""core/dependencies.py — payment_service"""
from __future__ import annotations
import uuid
from dataclasses import dataclass
from typing import Annotated, Optional
import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from core.config import settings
from core.exceptions import UnauthorisedError, ForbiddenError
from db.session import get_async_session

_bearer = HTTPBearer(auto_error=False)


@dataclass
class TokenClaims:
    sub:          uuid.UUID
    org_id:       Optional[uuid.UUID] = None
    org_role:     Optional[str]       = None
    platform_role: Optional[str]      = None


async def get_db(session: AsyncSession = Depends(get_async_session)) -> AsyncSession:
    yield session


async def get_current_token(
    creds: Annotated[Optional[HTTPAuthorizationCredentials], Depends(_bearer)]
) -> TokenClaims:
    if not creds:
        raise UnauthorisedError()
    try:
        payload = jwt.decode(
            creds.credentials,
            settings.AUTH_SECRET_KEY,
            algorithms=[settings.AUTH_ALGORITHM],
        )
        return TokenClaims(
            sub          = uuid.UUID(payload["sub"]),
            org_id       = uuid.UUID(payload["org_id"]) if payload.get("org_id") else None,
            org_role     = payload.get("org_role"),
            platform_role = payload.get("platform_role"),
        )
    except Exception:
        raise UnauthorisedError()


async def require_auth(token: TokenClaims = Depends(get_current_token)) -> TokenClaims:
    return token


async def require_staff(token: TokenClaims = Depends(get_current_token)) -> TokenClaims:
    """Require org_role=manager+ or platform_role=admin+"""
    allowed_org   = {"owner", "admin", "manager"}
    allowed_plat  = {"super_admin", "admin", "moderator"}
    if token.org_role in allowed_org or token.platform_role in allowed_plat:
        return token
    raise ForbiddenError()


async def get_client_ip(request: Request) -> str:
    xff = request.headers.get("X-Forwarded-For")
    return xff.split(",")[0].strip() if xff else (request.client.host if request.client else "unknown")


DbDep    = Annotated[AsyncSession, Depends(get_db)]
AuthDep  = Annotated[TokenClaims, Depends(require_auth)]
StaffDep = Annotated[TokenClaims, Depends(require_staff)]

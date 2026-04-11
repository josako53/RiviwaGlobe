"""core/dependencies.py — FastAPI dependencies for ai_service."""
from __future__ import annotations
import uuid
from dataclasses import dataclass
from typing import Annotated, Optional
import structlog
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from core.config import settings
from core.exceptions import ForbiddenError, TokenExpiredError, TokenInvalidError, UnauthorisedError
from db.session import get_async_session

log = structlog.get_logger(__name__)
_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True, slots=True)
class TokenClaims:
    sub:           uuid.UUID
    jti:           uuid.UUID
    exp:           int
    org_id:        Optional[uuid.UUID]
    org_role:      Optional[str]
    platform_role: Optional[str]


def _decode(raw: str) -> TokenClaims:
    try:
        p = jwt.decode(raw, settings.AUTH_SECRET_KEY, algorithms=[settings.AUTH_ALGORITHM])
    except ExpiredSignatureError:
        raise TokenExpiredError()
    except JWTError:
        raise TokenInvalidError()
    try:
        return TokenClaims(
            sub           = uuid.UUID(p["sub"]),
            jti           = uuid.UUID(p.get("jti", str(uuid.uuid4()))),
            exp           = int(p["exp"]),
            org_id        = uuid.UUID(p["org_id"]) if p.get("org_id") else None,
            org_role      = p.get("org_role"),
            platform_role = p.get("platform_role"),
        )
    except (KeyError, ValueError):
        raise TokenInvalidError()


async def get_db(session: AsyncSession = Depends(get_async_session)) -> AsyncSession:
    return session


async def get_current_token(
    creds: Annotated[Optional[HTTPAuthorizationCredentials], Depends(_bearer)]
) -> TokenClaims:
    if not creds or not creds.credentials:
        raise UnauthorisedError()
    return _decode(creds.credentials)


async def get_optional_token(
    creds: Annotated[Optional[HTTPAuthorizationCredentials], Depends(_bearer)]
) -> Optional[TokenClaims]:
    if not creds or not creds.credentials:
        return None
    try:
        return _decode(creds.credentials)
    except (TokenExpiredError, TokenInvalidError):
        return None


_PLATFORM_PRIORITY = {"super_admin": 3, "admin": 2, "moderator": 1}
_ORG_PRIORITY      = {"owner": 3, "admin": 2, "manager": 1, "member": 0}


def _is_platform_admin(token: TokenClaims) -> bool:
    return _PLATFORM_PRIORITY.get(token.platform_role or "", 0) >= 2


async def require_staff(token: Annotated[TokenClaims, Depends(get_current_token)]) -> TokenClaims:
    if _is_platform_admin(token):
        return token
    if not token.org_id:
        raise ForbiddenError(message="Switch to an active organisation to access AI sessions.")
    if token.org_role not in ("owner", "admin", "manager", "member"):
        raise ForbiddenError(message="You must be a member of an organisation.")
    return token


DbDep       = Annotated[AsyncSession, Depends(get_db)]
StaffDep    = Annotated[TokenClaims,  Depends(require_staff)]
OptTokenDep = Annotated[Optional[TokenClaims], Depends(get_optional_token)]

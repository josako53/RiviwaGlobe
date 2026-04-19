"""core/dependencies.py"""
from __future__ import annotations
import uuid
from dataclasses import dataclass
from typing import Annotated, Callable, Optional
import structlog
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from core.config import settings
from core.exceptions import ForbiddenError, TokenExpiredError, TokenInvalidError, UnauthorisedError
from db.session import get_async_session
from events.producer import FeedbackProducer, get_producer

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
            org_role      = (p.get("org_role") or "").lower() or None,
            platform_role = p.get("platform_role"),
        )
    except (KeyError, ValueError):
        raise TokenInvalidError()


async def get_db(session: AsyncSession = Depends(get_async_session)) -> AsyncSession:
    return session


async def get_kafka() -> FeedbackProducer:
    return await get_producer()


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
    """GRM read access: any org member OR platform admin."""
    if _is_platform_admin(token):
        return token
    if not token.org_id:
        raise ForbiddenError(message="Switch to an active organisation to access GRM.")
    if token.org_role not in ("owner", "admin", "manager", "member"):
        raise ForbiddenError(message="You must be a member of an organisation to access GRM.")
    return token


async def require_grm_officer(token: Annotated[TokenClaims, Depends(get_current_token)]) -> TokenClaims:
    """GRM write access: manager/admin/owner OR platform admin.
    Used for: submit, acknowledge, assign, escalate, resolve, close."""
    if _is_platform_admin(token):
        return token
    if not token.org_id:
        raise ForbiddenError(message="Switch to an active organisation to perform this action.")
    if _ORG_PRIORITY.get(token.org_role or "", -1) < 1:
        raise ForbiddenError(message="Requires org role 'manager' or higher.")
    return token


async def require_grm_coordinator(token: Annotated[TokenClaims, Depends(get_current_token)]) -> TokenClaims:
    """Senior GRM access: admin/owner OR platform admin.
    Used for: dismiss (irreversible closure)."""
    if _is_platform_admin(token):
        return token
    if not token.org_id:
        raise ForbiddenError(message="Switch to an active organisation to perform this action.")
    if _ORG_PRIORITY.get(token.org_role or "", -1) < 2:
        raise ForbiddenError(message="Requires org role 'admin' or higher.")
    return token


def require_platform_role(role: str) -> Callable:
    required = _PLATFORM_PRIORITY.get(role, 0)

    async def _guard(token: Annotated[TokenClaims, Depends(get_current_token)]) -> TokenClaims:
        actual = _PLATFORM_PRIORITY.get(token.platform_role or "", 0)
        if actual < required:
            raise ForbiddenError(message=f"Requires platform role '{role}' or higher.")
        return token
    return _guard


async def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


DbDep              = Annotated[AsyncSession,     Depends(get_db)]
KafkaDep           = Annotated[FeedbackProducer, Depends(get_kafka)]
StaffDep           = Annotated[TokenClaims,      Depends(require_staff)]
GRMOfficerDep      = Annotated[TokenClaims,      Depends(require_grm_officer)]
GRMCoordinatorDep  = Annotated[TokenClaims,      Depends(require_grm_coordinator)]
OptTokenDep        = Annotated[Optional[TokenClaims], Depends(get_optional_token)]

# Consumer portal — any authenticated user (Consumer or staff)
# ConsumerDep uses the same JWT as StaffDep but does not require a staff role.
# The Consumer portal uses ownership checks (submitted_by_user_id == token.sub)
# to ensure Consumers only see their own data.
async def require_authenticated(token: TokenClaims = Depends(get_current_token)) -> TokenClaims:
    """Require a valid JWT but no specific role. Used for Consumer self-service endpoints."""
    return token

ConsumerDep = Annotated[TokenClaims, Depends(require_authenticated)]
CurrentUserDep = Annotated[TokenClaims, Depends(get_current_token)]

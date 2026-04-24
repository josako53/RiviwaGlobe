"""core/dependencies.py — FastAPI dependency injection for analytics_service."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Annotated, Optional

import structlog
from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.exceptions import (
    ForbiddenError,
    TokenExpiredError,
    TokenInvalidError,
    UnauthorisedError,
)
from db.session import get_analytics_session, get_feedback_session

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


# ── JWT dependencies ──────────────────────────────────────────────────────────

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


# ── Role helpers ──────────────────────────────────────────────────────────────

_PLATFORM_PRIORITY = {"super_admin": 3, "admin": 2, "moderator": 1}
_ORG_PRIORITY      = {"owner": 3, "admin": 2, "manager": 1, "member": 0}


def _is_platform_admin(token: TokenClaims) -> bool:
    return _PLATFORM_PRIORITY.get(token.platform_role or "", 0) >= 2


async def require_staff(
    token: Annotated[TokenClaims, Depends(get_current_token)]
) -> TokenClaims:
    """Read access: any org member OR platform admin."""
    if _is_platform_admin(token):
        return token
    if not token.org_id:
        raise ForbiddenError(message="Switch to an active organisation to access analytics.")
    if token.org_role not in ("owner", "admin", "manager", "member"):
        raise ForbiddenError(message="You must be a member of an organisation to access analytics.")
    return token


async def require_grm_officer(
    token: Annotated[TokenClaims, Depends(get_current_token)]
) -> TokenClaims:
    """GRM write/analytics access: manager/admin/owner OR platform admin."""
    if _is_platform_admin(token):
        return token
    if not token.org_id:
        raise ForbiddenError(message="Switch to an active organisation to perform this action.")
    if _ORG_PRIORITY.get(token.org_role or "", -1) < 1:
        raise ForbiddenError(message="Requires org role 'manager' or higher.")
    return token


async def require_org_admin(
    token: Annotated[TokenClaims, Depends(get_current_token)]
) -> TokenClaims:
    """Admin analytics access: admin/owner OR platform admin."""
    if _is_platform_admin(token):
        return token
    if not token.org_id:
        raise ForbiddenError(message="Switch to an active organisation to perform this action.")
    if _ORG_PRIORITY.get(token.org_role or "", -1) < 2:
        raise ForbiddenError(message="Requires org role 'admin' or higher.")
    return token


# ── Org-scope enforcement helpers ────────────────────────────────────────────

def assert_org_access(token: TokenClaims, requested_org_id: "uuid.UUID") -> None:
    """
    Raise 403 if a non-platform-admin tries to access a different org's data.
    Platform admins (super_admin/admin) can access any org.
    """
    import uuid as _uuid
    if _is_platform_admin(token):
        return
    if not token.org_id:
        raise ForbiddenError(message="Switch to an active organisation to access analytics.")
    if token.org_id != requested_org_id:
        raise ForbiddenError(message="You do not have access to this organisation's data.")


def assert_project_org_access(token: TokenClaims, project_org_id: "Optional[uuid.UUID]") -> None:
    """
    After resolving a project's organisation_id, enforce that the token's
    org matches. Skipped for platform admins or when org cannot be determined.
    """
    if _is_platform_admin(token):
        return
    if project_org_id and token.org_id and token.org_id != project_org_id:
        raise ForbiddenError(message="This project belongs to a different organisation.")


# ── Internal service key dependency ──────────────────────────────────────────

async def require_internal_key(
    x_service_key: Annotated[Optional[str], Header(alias="X-Service-Key")] = None,
) -> None:
    if not x_service_key or x_service_key != settings.INTERNAL_SERVICE_KEY:
        raise ForbiddenError(message="Invalid or missing service key.")


# ── DB session dependencies ───────────────────────────────────────────────────

async def get_analytics_db(
    session: AsyncSession = Depends(get_analytics_session),
) -> AsyncSession:
    return session


async def get_feedback_db(
    session: AsyncSession = Depends(get_feedback_session),
) -> AsyncSession:
    return session


# ── Client IP helper ──────────────────────────────────────────────────────────

async def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ── Typed annotation aliases ──────────────────────────────────────────────────

CurrentUser        = Annotated[TokenClaims, Depends(get_current_token)]
OptTokenDep        = Annotated[Optional[TokenClaims], Depends(get_optional_token)]
StaffDep           = Annotated[TokenClaims, Depends(require_staff)]
GRMOfficerDep      = Annotated[TokenClaims, Depends(require_grm_officer)]
OrgAdminDep        = Annotated[TokenClaims, Depends(require_org_admin)]
AnalyticsDbDep     = Annotated[AsyncSession, Depends(get_analytics_db)]

# Re-export so routers import from one place
__all__ = [
    "assert_org_access", "assert_project_org_access",
    "TokenClaims", "_is_platform_admin",
    "CurrentUser", "OptTokenDep", "StaffDep", "GRMOfficerDep", "OrgAdminDep",
    "AnalyticsDbDep", "FeedbackDbDep",
]
FeedbackDbDep      = Annotated[AsyncSession, Depends(get_feedback_db)]
InternalKeyDep     = Depends(require_internal_key)

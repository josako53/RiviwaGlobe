"""
core/dependencies.py
═══════════════════════════════════════════════════════════════════════════════
FastAPI dependency injection for stakeholder_service.

JWT VALIDATION
──────────────────────────────────────────────────────────────────────────────
  Tokens are issued by auth_service (HS256, same SECRET_KEY).
  stakeholder_service validates them locally — no HTTP call to auth_service.

  Token claims used:
    sub          → user_id (UUID)
    org_id       → active org dashboard context (optional)
    platform_role → super_admin | admin | moderator | null
    org_role      → owner | admin | manager | member | null (within active org)
    exp, jti

  There is NO JTI deny-list check here — stakeholder_service does not have
  access to auth_service's Redis. Tokens are accepted until natural expiry.
  For revocation sensitivity, keep ACCESS_TOKEN_EXPIRE_MINUTES short (30 min).

ROLE GUARDS
──────────────────────────────────────────────────────────────────────────────
  require_staff         → any authenticated user (PIU staff — any active JWT)
  require_platform_role → user must have specific platform_role in JWT
    e.g. require_platform_role("admin") for admin-only endpoints

  PIU field officers (no platform_role, just a JWT) can read and write most
  stakeholder/engagement data. Destructive operations require admin.
═══════════════════════════════════════════════════════════════════════════════
"""
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
from events.producer import StakeholderProducer, get_producer

log = structlog.get_logger(__name__)

_bearer = HTTPBearer(auto_error=False)


# ─────────────────────────────────────────────────────────────────────────────
# Token claims dataclass
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class TokenClaims:
    sub:           uuid.UUID
    jti:           uuid.UUID
    exp:           int
    org_id:        Optional[uuid.UUID]
    org_role:      Optional[str]
    platform_role: Optional[str]


# ─────────────────────────────────────────────────────────────────────────────
# Token decoder
# ─────────────────────────────────────────────────────────────────────────────

def _decode_token(raw: str) -> TokenClaims:
    try:
        payload = jwt.decode(
            raw,
            settings.AUTH_SECRET_KEY,
            algorithms=[settings.AUTH_ALGORITHM],
        )
    except ExpiredSignatureError:
        raise TokenExpiredError()
    except JWTError:
        raise TokenInvalidError()

    try:
        return TokenClaims(
            sub           = uuid.UUID(payload["sub"]),
            jti           = uuid.UUID(payload.get("jti", str(uuid.uuid4()))),
            exp           = int(payload["exp"]),
            org_id        = uuid.UUID(payload["org_id"]) if payload.get("org_id") else None,
            org_role      = payload.get("org_role"),
            platform_role = payload.get("platform_role"),
        )
    except (KeyError, ValueError, TypeError):
        raise TokenInvalidError()


# ─────────────────────────────────────────────────────────────────────────────
# Core dependencies
# ─────────────────────────────────────────────────────────────────────────────

async def get_db(session: AsyncSession = Depends(get_async_session)) -> AsyncSession:
    return session


async def get_kafka(producer: StakeholderProducer = Depends(get_producer)) -> StakeholderProducer:
    return producer


async def get_current_token(
    creds: Annotated[Optional[HTTPAuthorizationCredentials], Depends(_bearer)],
) -> TokenClaims:
    """Decode and validate the Bearer JWT. Raises if missing or invalid."""
    if not creds or not creds.credentials:
        raise UnauthorisedError()
    return _decode_token(creds.credentials)


async def get_optional_token(
    creds: Annotated[Optional[HTTPAuthorizationCredentials], Depends(_bearer)],
) -> Optional[TokenClaims]:
    """
    Return token claims if a valid Bearer token is present, else None.
    Used on endpoints that are accessible anonymously but provide richer
    responses to authenticated users.
    """
    if not creds or not creds.credentials:
        return None
    try:
        return _decode_token(creds.credentials)
    except (TokenExpiredError, TokenInvalidError):
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Role guards
# ─────────────────────────────────────────────────────────────────────────────

async def require_staff(
    token: Annotated[TokenClaims, Depends(get_current_token)],
) -> TokenClaims:
    """
    Any authenticated user — PIU field officers, admins, everyone with a JWT.
    The minimum bar for any write operation.
    """
    return token


def require_platform_role(role: str) -> Callable:
    """
    Factory: returns a dependency that enforces a minimum platform_role.

    Priority order (highest to lowest): super_admin → admin → moderator
    A super_admin satisfies require_platform_role("admin").

    Usage:
        @router.delete("/{id}", dependencies=[Depends(require_platform_role("admin"))])
    """
    _priority = {"super_admin": 3, "admin": 2, "moderator": 1}
    required  = _priority.get(role, 0)

    async def _guard(token: Annotated[TokenClaims, Depends(get_current_token)]) -> TokenClaims:
        actual = _priority.get(token.platform_role or "", 0)
        if actual < required:
            raise ForbiddenError(
                message=f"Requires platform role '{role}' or higher.",
                detail={"required": role, "actual": token.platform_role},
            )
        return token

    return _guard


# ─────────────────────────────────────────────────────────────────────────────
# Utility
# ─────────────────────────────────────────────────────────────────────────────

async def get_client_ip(request: Request) -> str:
    """Extract real client IP, respecting X-Forwarded-For if TRUST_PROXY."""
    if getattr(settings, "TRUST_PROXY", False):
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ─────────────────────────────────────────────────────────────────────────────
# Annotated shorthand aliases
# ─────────────────────────────────────────────────────────────────────────────

DbDep      = Annotated[AsyncSession,         Depends(get_db)]
KafkaDep   = Annotated[StakeholderProducer,  Depends(get_kafka)]
StaffDep   = Annotated[TokenClaims,          Depends(require_staff)]
TokenDep   = Annotated[TokenClaims,          Depends(get_current_token)]
OptTokenDep = Annotated[Optional[TokenClaims], Depends(get_optional_token)]

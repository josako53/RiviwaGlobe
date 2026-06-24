from __future__ import annotations
import uuid
from dataclasses import dataclass
from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.exceptions import ForbiddenError, UnauthorisedError
from core.security import decode_token
from db.session import get_async_session

_bearer = HTTPBearer(auto_error=False)

# ── DB dependency ──────────────────────────────────────────────────────────────

DbDep = Annotated[AsyncSession, Depends(get_async_session)]


# ── Token claims ───────────────────────────────────────────────────────────────

@dataclass
class TokenClaims:
    user_id:       uuid.UUID
    org_id:        Optional[uuid.UUID]
    platform_role: Optional[str]
    org_role:      Optional[str]
    email:         Optional[str]


def _decode(token: str) -> dict:
    payload = decode_token(token)
    if not payload:
        raise UnauthorisedError()
    return payload


def _claims(payload: dict) -> TokenClaims:
    try:
        raw_org = payload.get("org_id")
        return TokenClaims(
            user_id=uuid.UUID(payload["sub"]),
            org_id=uuid.UUID(raw_org) if raw_org else None,
            platform_role=payload.get("platform_role"),
            org_role=payload.get("org_role"),
            email=payload.get("email"),
        )
    except (KeyError, ValueError) as exc:
        raise UnauthorisedError() from exc


# ── Auth variants ──────────────────────────────────────────────────────────────

def _is_platform_admin(payload: dict) -> bool:
    role = (payload.get("platform_role") or "").lower()
    return role in ("super_admin", "admin")


def _is_org_staff(payload: dict) -> bool:
    role = (payload.get("org_role") or "").lower()
    return role in ("owner", "admin", "manager", "editor")


async def require_authenticated(
    creds: Annotated[Optional[HTTPAuthorizationCredentials], Depends(_bearer)],
) -> TokenClaims:
    if not creds or not creds.credentials:
        raise UnauthorisedError()
    return _claims(_decode(creds.credentials))


async def optional_token(
    creds: Annotated[Optional[HTTPAuthorizationCredentials], Depends(_bearer)],
) -> Optional[TokenClaims]:
    if not creds or not creds.credentials:
        return None
    try:
        return _claims(_decode(creds.credentials))
    except Exception:
        return None


async def require_staff(
    creds: Annotated[Optional[HTTPAuthorizationCredentials], Depends(_bearer)],
) -> TokenClaims:
    if not creds or not creds.credentials:
        raise UnauthorisedError()
    payload = _decode(creds.credentials)
    if not (_is_platform_admin(payload) or _is_org_staff(payload)):
        raise ForbiddenError(message="Staff or admin access required.")
    return _claims(payload)


async def require_service_key(
    x_service_key: Annotated[Optional[str], Header(alias="X-Service-Key")] = None,
    x_internal_key: Annotated[Optional[str], Header(alias="X-Internal-Service-Key")] = None,
) -> None:
    key = x_service_key or x_internal_key
    if not key or key != settings.INTERNAL_SERVICE_KEY:
        raise UnauthorisedError()


# ── Annotated deps ─────────────────────────────────────────────────────────────

AuthDep     = Annotated[TokenClaims, Depends(require_authenticated)]
StaffDep    = Annotated[TokenClaims, Depends(require_staff)]
InternalDep = Annotated[None, Depends(require_service_key)]
OptTokenDep = Annotated[Optional[TokenClaims], Depends(optional_token)]

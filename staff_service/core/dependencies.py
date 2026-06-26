from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Optional

import httpx
import structlog
from fastapi import Depends, Header, HTTPException
from jose import ExpiredSignatureError, JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.exceptions import ForbiddenError, TokenExpiredError, TokenInvalidError
from db.session import get_async_session
from events.producer import StaffProducer, get_producer


@dataclass(frozen=True)
class TokenClaims:
    sub: str                      # user UUID
    jti: str                      # token ID (deny-list)
    org_id: Optional[str]         # active org UUID
    org_role: Optional[str]       # owner | admin | manager | member
    platform_role: Optional[str]  # super_admin | admin | moderator


_ORG_ROLE_RANK = {"owner": 3, "admin": 2, "manager": 1, "member": 0}
_PLATFORM_ROLE_RANK = {"super_admin": 3, "admin": 2, "moderator": 1}


def _decode(token: str) -> TokenClaims:
    try:
        payload = jwt.decode(
            token,
            settings.AUTH_SECRET_KEY,
            algorithms=[settings.AUTH_ALGORITHM],
        )
    except ExpiredSignatureError:
        raise TokenExpiredError()
    except JWTError:
        raise TokenInvalidError()

    return TokenClaims(
        sub=payload.get("sub", ""),
        jti=payload.get("jti", ""),
        org_id=payload.get("org_id"),
        org_role=payload.get("org_role"),
        platform_role=payload.get("platform_role"),
    )


def _is_platform_admin(claims: TokenClaims) -> bool:
    return _PLATFORM_ROLE_RANK.get((claims.platform_role or "").lower(), -1) >= 2


def _org_rank(claims: TokenClaims) -> int:
    return _ORG_ROLE_RANK.get((claims.org_role or "").lower(), -1)


async def get_current_user(
    authorization: Annotated[Optional[str], Header()] = None,
) -> TokenClaims:
    if not authorization or not authorization.startswith("Bearer "):
        raise TokenInvalidError()
    try:
        return _decode(authorization.split(" ", 1)[1])
    except (TokenExpiredError, TokenInvalidError):
        raise
    except Exception:
        raise TokenInvalidError()


async def get_optional_user(
    authorization: Annotated[Optional[str], Header()] = None,
) -> Optional[TokenClaims]:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        return _decode(authorization.split(" ", 1)[1])
    except Exception:
        return None


async def require_authenticated(
    claims: Annotated[TokenClaims, Depends(get_current_user)],
) -> TokenClaims:
    return claims


async def require_staff_member(
    claims: Annotated[TokenClaims, Depends(get_current_user)],
) -> TokenClaims:
    """Any org member (member+) or platform admin."""
    if _is_platform_admin(claims):
        return claims
    if _org_rank(claims) < 0:
        raise ForbiddenError()
    return claims


async def require_manager(
    claims: Annotated[TokenClaims, Depends(get_current_user)],
) -> TokenClaims:
    """Manager+ or platform admin."""
    if _is_platform_admin(claims):
        return claims
    if _org_rank(claims) < 1:
        raise ForbiddenError()
    return claims


async def require_admin(
    claims: Annotated[TokenClaims, Depends(get_current_user)],
) -> TokenClaims:
    """Admin+ or platform admin."""
    if _is_platform_admin(claims):
        return claims
    if _org_rank(claims) < 2:
        raise ForbiddenError()
    return claims


async def require_internal(
    x_internal_service_key: Annotated[Optional[str], Header()] = None,
) -> None:
    if x_internal_service_key != settings.INTERNAL_SERVICE_KEY:
        raise HTTPException(status_code=401, detail="Invalid internal service key")


async def require_api_key(
    x_api_key: Annotated[Optional[str], Header()] = None,
) -> None:
    """Third-party API key auth — accept INTERNAL_SERVICE_KEY value for now."""
    if x_api_key != settings.INTERNAL_SERVICE_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


# ── Type aliases for clean route signatures ───────────────────────────────────

DbDep = Annotated[AsyncSession, Depends(get_async_session)]
KafkaDep = Annotated[StaffProducer, Depends(get_producer)]
AuthDep = Annotated[TokenClaims, Depends(require_authenticated)]
StaffDep = Annotated[TokenClaims, Depends(require_staff_member)]
ManagerDep = Annotated[TokenClaims, Depends(require_manager)]
AdminDep = Annotated[TokenClaims, Depends(require_admin)]
OptTokenDep = Annotated[Optional[TokenClaims], Depends(get_optional_user)]
InternalDep = Annotated[None, Depends(require_internal)]
ApiKeyDep = Annotated[None, Depends(require_api_key)]

log = structlog.get_logger(__name__)


def require_feature(feature: str):
    """Subscription feature-gate. Raises HTTP 402 if not on plan, 503 if unreachable."""
    async def _gate(token: Annotated[TokenClaims, Depends(get_current_user)]) -> None:
        if not token.org_id:
            raise HTTPException(
                status_code=403,
                detail={"error": "NO_ACTIVE_ORG",
                        "message": "Switch to an active organisation to use this feature."},
            )
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{settings.SUBSCRIPTION_SERVICE_URL}/api/v1/subscriptions/internal/feature-check",
                    params={"org_id": str(token.org_id), "feature": feature},
                    headers={"X-Service-Key": settings.INTERNAL_SERVICE_KEY},
                )
        except Exception as exc:
            log.warning("subscription.check.unavailable", feature=feature, error=str(exc))
            raise HTTPException(
                status_code=503,
                detail={"error": "SUBSCRIPTION_CHECK_FAILED",
                        "message": "Unable to verify subscription. Please try again."},
            )
        if resp.status_code != 200 or not resp.json().get("has_access"):
            raise HTTPException(
                status_code=402,
                detail={"error": "FEATURE_NOT_AVAILABLE", "feature": feature,
                        "message": f"Your current plan does not include '{feature}'. "
                                    "Upgrade your subscription to access this feature."},
            )
    return _gate

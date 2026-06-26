"""core/dependencies.py — payment_service"""
from __future__ import annotations
import httpx
import structlog
import uuid
from dataclasses import dataclass
from typing import Annotated, Optional
import jwt
from fastapi import Depends, HTTPException, Request

log = structlog.get_logger(__name__)
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
            org_role     = (payload.get("org_role") or "").lower() or None,
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


async def require_platform_admin(token: TokenClaims = Depends(get_current_token)) -> TokenClaims:
    """Restrict to platform_role=admin or super_admin only. Used for disbursements."""
    if token.platform_role in {"admin", "super_admin"}:
        return token
    raise ForbiddenError()


async def get_client_ip(request: Request) -> str:
    xff = request.headers.get("X-Forwarded-For")
    return xff.split(",")[0].strip() if xff else (request.client.host if request.client else "unknown")


DbDep                = Annotated[AsyncSession, Depends(get_db)]
AuthDep              = Annotated[TokenClaims, Depends(require_auth)]
StaffDep             = Annotated[TokenClaims, Depends(require_staff)]
PlatformAdminDep     = Annotated[TokenClaims, Depends(require_platform_admin)]


def require_feature(feature: str):
    """Subscription feature-gate. Raises HTTP 402 if not on plan, 503 if unreachable."""
    async def _gate(token: Annotated[TokenClaims, Depends(get_current_token)]) -> None:
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

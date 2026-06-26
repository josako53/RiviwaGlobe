"""core/dependencies.py — Shared FastAPI dependencies."""
from __future__ import annotations

from typing import Annotated, Optional

import httpx
import structlog
from fastapi import Depends, Header, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from db.session import AsyncSessionLocal

log = structlog.get_logger(__name__)


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


# ── Subscription feature-gate ─────────────────────────────────────────────────

def require_feature(feature: str):
    """Subscription feature-gate. Verifies the org's active plan includes `feature`.
    Raises HTTP 402 if not on plan, 503 if subscription service unreachable.
    Usage: @router.get("/path", dependencies=[Depends(require_feature("flag"))])
    """
    async def _gate(user: Annotated[dict, Depends(get_current_user)]) -> None:
        org_id = user.get("org_id")
        if not org_id:
            raise HTTPException(
                status_code=403,
                detail={"error": "NO_ACTIVE_ORG",
                        "message": "Switch to an active organisation to use this feature."},
            )
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{settings.SUBSCRIPTION_SERVICE_URL}/api/v1/subscriptions/internal/feature-check",
                    params={"org_id": str(org_id), "feature": feature},
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

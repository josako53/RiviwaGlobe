"""core/deps.py — FastAPI dependencies for subscription_service."""
from __future__ import annotations

from typing import Annotated, Optional
from fastapi import Depends, Header, HTTPException
import jwt

from core.config import settings
from db.session import get_async_session
from sqlalchemy.ext.asyncio import AsyncSession


# ── DB dependency ─────────────────────────────────────────────────────────────

DbDep = Annotated[AsyncSession, Depends(get_async_session)]


# ── JWT auth ──────────────────────────────────────────────────────────────────

def _decode_token(authorization: str = Header(default="")) -> Optional[dict]:
    if not authorization.lower().startswith("bearer "):
        return None
    token = authorization[7:]
    try:
        claims = jwt.decode(
            token,
            settings.AUTH_SECRET_KEY,
            algorithms=[settings.AUTH_ALGORITHM],
            options={"verify_aud": False},
        )
        claims["_raw_token"] = token   # passed downstream to payment_service
        return claims
    except Exception:
        return None


def _require_token(authorization: str = Header(default="")) -> dict:
    claims = _decode_token(authorization)
    if not claims:
        raise HTTPException(status_code=401, detail={"error": "UNAUTHORISED", "message": "Valid Bearer token required."})
    return claims


def _require_admin(authorization: str = Header(default="")) -> dict:
    claims = _require_token(authorization)
    role = claims.get("org_role", "")
    if role not in ("OWNER", "ADMIN", "SUPER_ADMIN"):
        raise HTTPException(status_code=403, detail={"error": "FORBIDDEN", "message": "Admin access required."})
    return claims


def _require_service_key(x_service_key: str = Header(default="")) -> None:
    if x_service_key != settings.INTERNAL_SERVICE_KEY:
        raise HTTPException(status_code=401, detail={"error": "INVALID_SERVICE_KEY"})


OptTokenDep    = Annotated[Optional[dict], Depends(_decode_token)]
TokenDep       = Annotated[dict, Depends(_require_token)]
AdminDep       = Annotated[dict, Depends(_require_admin)]
ServiceKeyDep  = Annotated[None, Depends(_require_service_key)]


def get_org_id(claims: TokenDep) -> str:
    org_id = claims.get("org_id")
    if not org_id:
        raise HTTPException(status_code=400, detail={"error": "NO_ORG", "message": "No active organisation in token."})
    return org_id


OrgIdDep = Annotated[str, Depends(get_org_id)]


# ── Feature gate dependency ───────────────────────────────────────────────────

def require_feature(feature_key: str):
    """
    FastAPI dependency factory for feature-gating endpoints.

    Usage:
        @router.post("/endpoint", dependencies=[Depends(require_feature("webhooks"))])

    Raises HTTP 403 with FEATURE_NOT_AVAILABLE if the org subscription
    does not include the feature or the subscription is not active.
    """
    async def _check(
        authorization: str = Header(default=""),
        db: AsyncSession = Depends(get_async_session),
    ) -> None:
        claims = _decode_token(authorization)
        if not claims:
            raise HTTPException(status_code=401, detail={"error": "UNAUTHORISED"})
        org_id = claims.get("org_id")
        if not org_id:
            raise HTTPException(status_code=400, detail={"error": "NO_ORG"})
        from services.subscription_svc import SubscriptionService
        svc = SubscriptionService(db)
        has_access = await svc.check_feature(org_id, feature_key)
        if not has_access:
            raise HTTPException(
                status_code=403,
                detail={
                    "error":   "FEATURE_NOT_AVAILABLE",
                    "message": f"Your plan does not include {feature_key!r}. Upgrade at /api/v1/plans.",
                    "feature": feature_key,
                },
            )
    return Depends(_check)


FeatureGateDep = require_feature  # alias for readability

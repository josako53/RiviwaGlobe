from __future__ import annotations
import httpx
import structlog
from fastapi import Depends, Header, HTTPException
from jose import jwt, JWTError
from core.config import settings

log = structlog.get_logger(__name__)


def _require_jwt(authorization: str = Header(default="")):
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail={"error": "MISSING_TOKEN"})
    token = authorization[7:]
    try:
        payload = jwt.decode(
            token, settings.AUTH_SECRET_KEY,
            algorithms=[settings.AUTH_ALGORITHM],
            options={"verify_aud": False},
        )
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail={"error": "INVALID_TOKEN"})


JWTDep = Depends(_require_jwt)


def require_feature(feature: str):
    """Subscription feature-gate. Raises HTTP 402 if not on plan, 503 if unreachable."""
    async def _gate(claims: dict = JWTDep) -> None:
        org_id = (claims or {}).get("org_id")
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

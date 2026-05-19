"""services/auth_client.py — Internal calls to auth_service."""
from __future__ import annotations

import asyncio
import structlog
import httpx

from core.config import settings

log = structlog.get_logger(__name__)

_AUTH_BASE = "http://riviwa_auth_service:8000/api/v1"


async def _set_payment_verified(org_id: str) -> None:
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.post(
                f"{_AUTH_BASE}/internal/orgs/{org_id}/set-payment-verified",
                headers={"X-Service-Key": settings.INTERNAL_SERVICE_KEY},
            )
            if r.status_code == 200:
                log.info("auth_client.payment_verified", org_id=org_id)
            else:
                log.warning("auth_client.payment_verified_failed",
                            org_id=org_id, status=r.status_code, body=r.text[:200])
    except Exception as exc:
        log.error("auth_client.payment_verified_error", org_id=org_id, error=str(exc))


def notify_payment_verified(org_id: str) -> None:
    """Fire-and-forget — never blocks the checkout path."""
    asyncio.ensure_future(_set_payment_verified(org_id))

"""services/auth_client.py — Internal HTTP client to auth_service."""
from __future__ import annotations
import uuid
from typing import Optional
import httpx
import structlog
from core.config import settings

log = structlog.get_logger(__name__)

_INTERNAL_HEADERS = {
    "X-Service-Key": settings.INTERNAL_SERVICE_KEY,
    "X-Service-Name": "ai_service",
}


class AuthClient:
    """
    Calls auth_service to:
    1. Look up a Consumer by phone number
    2. Register a new Consumer (quick registration: name + phone)
    """

    async def find_user_by_phone(self, phone: str) -> Optional[dict]:
        """Returns user dict if found, None if not registered."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(
                    f"{settings.AUTH_SERVICE_URL}/api/v1/users/by-phone",
                    params={"phone": phone},
                    headers=_INTERNAL_HEADERS,
                )
                if r.status_code == 200:
                    return r.json()
                return None
        except Exception as exc:
            log.warning("auth_client.find_phone_failed", phone=phone, error=str(exc))
            return None

    async def register_consumer(self, name: str, phone: str) -> Optional[dict]:
        """
        Quick-register a Consumer with name and phone.
        Returns created user dict or None on failure.
        """
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.post(
                    f"{settings.AUTH_SERVICE_URL}/api/v1/users/register-consumer",
                    json={"full_name": name, "phone": phone},
                    headers=_INTERNAL_HEADERS,
                )
                if r.status_code in (200, 201):
                    log.info("auth_client.consumer_registered", phone=phone)
                    return r.json()
                log.warning(
                    "auth_client.register_failed",
                    status=r.status_code,
                    body=r.text[:200],
                )
                return None
        except Exception as exc:
            log.error("auth_client.register_error", error=str(exc))
            return None

    async def get_feedback_status(self, unique_ref: str) -> Optional[dict]:
        """
        Proxy to feedback_service to look up a status by reference number.
        Used by auth_client only as a convenience method.
        """
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(
                    f"{settings.FEEDBACK_SERVICE_URL}/api/v1/feedback",
                    params={"unique_ref": unique_ref},
                    headers=_INTERNAL_HEADERS,
                )
                if r.status_code == 200:
                    items = r.json().get("items", [])
                    return items[0] if items else None
                return None
        except Exception as exc:
            log.warning("auth_client.status_failed", ref=unique_ref, error=str(exc))
            return None

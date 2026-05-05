"""services/image_intelligence_client.py — Call ai_service image intelligence pipeline."""
from __future__ import annotations

import base64
from typing import Optional

import httpx
import structlog

from core.config import settings

log = structlog.get_logger(__name__)


async def analyze_fake_image(
    image_bytes: bytes,
    org_id: Optional[str] = None,
    short_code: Optional[str] = None,
    location: Optional[str] = None,
) -> Optional[dict]:
    """
    Send a suspected counterfeit image to ai_service for CLIP + Llama 4 Scout analysis.

    Returns the structured verdict dict, or None if ai_service is unreachable.
    """
    payload: dict = {
        "image_base64": base64.b64encode(image_bytes).decode(),
    }
    if org_id:
        payload["org_id"] = org_id
    if short_code:
        payload["short_code"] = short_code
    if location:
        payload["location"] = location

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(
                f"{settings.AI_SERVICE_URL}/api/v1/ai/internal/image/analyze",
                json=payload,
                headers={"X-Service-Key": settings.INTERNAL_SERVICE_KEY},
            )
        if resp.status_code == 200:
            return resp.json()
        log.warning("image_intelligence_client.non_200",
                    status=resp.status_code, body=resp.text[:200])
    except Exception as exc:
        log.warning("image_intelligence_client.failed", error=str(exc))

    return None

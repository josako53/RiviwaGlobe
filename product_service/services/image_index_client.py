"""services/image_index_client.py — Index product images into ai_service Qdrant collection."""
from __future__ import annotations

from typing import Optional
from uuid import UUID

import httpx
import structlog

from core.config import settings

log = structlog.get_logger(__name__)


async def index_product_images(
    product_id: UUID,
    org_id: UUID,
    image_urls: list[str],
    title: str = "",
    brand: str = "",
    rsin: str = "",
    image_roles: Optional[list[str]] = None,
) -> None:
    """
    Fire-and-forget: index product images into ai_service Qdrant collection.
    Called when a product is published so the AI counterfeit detection pipeline
    can find genuine product images for comparison.
    """
    if not image_urls:
        return

    payload = {
        "product_id": str(product_id),
        "org_id":     str(org_id),
        "image_urls": image_urls,
        "title":      title,
        "brand":      brand,
        "rsin":       rsin,
    }
    if image_roles:
        payload["image_roles"] = image_roles

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.AI_SERVICE_URL}/api/v1/ai/internal/image/index",
                json=payload,
                headers={"X-Service-Key": settings.INTERNAL_SERVICE_KEY},
            )
        if resp.status_code == 201:
            data = resp.json()
            log.info("product.images_indexed",
                     product_id=str(product_id),
                     indexed=data.get("indexed_count"),
                     total=data.get("total_urls"))
        else:
            log.warning("product.image_index_failed",
                        product_id=str(product_id),
                        status=resp.status_code,
                        body=resp.text[:200])
    except Exception as exc:
        log.warning("product.image_index_error", product_id=str(product_id), error=str(exc))

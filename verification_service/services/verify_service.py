"""services/verify_service.py — Core verification decision engine."""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional, Tuple

import httpx
import structlog

from core.config import settings

log = structlog.get_logger(__name__)


async def resolve_code(raw_code: str) -> Tuple[Optional[dict], str]:
    """
    Call qr_service to look up a QR code or SMS code.
    Returns (qr_data_or_None, clean_short_code).
    """
    code = raw_code.strip().upper()
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(
            f"{settings.QR_SERVICE_URL}/api/v1/internal/qr/lookup",
            params={"short_code": code},
            headers={"X-Service-Key": settings.INTERNAL_SERVICE_KEY},
        )
        if resp.status_code == 200:
            return resp.json(), code
    return None, code


async def increment_scan_count(
    qr_code_id: str,
    short_code: str,
    scanner_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    """
    Tell qr_service to increment scan_count and record a QRScan row.
    Fire-and-forget — never raises so it never blocks the verify response.
    """
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            await client.post(
                f"{settings.QR_SERVICE_URL}/api/v1/internal/qr/increment-scan",
                json={
                    "qr_code_id": qr_code_id,
                    "short_code":  short_code,
                    "scanner_ip":  scanner_ip,
                    "user_agent":  user_agent,
                },
                headers={"X-Service-Key": settings.INTERNAL_SERVICE_KEY},
            )
    except Exception as exc:
        log.warning("verify.increment_scan.failed", qr_code_id=qr_code_id, error=str(exc))


async def fetch_product_details(product_id: str) -> Optional[dict]:
    """Fetch product information from product_service."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{settings.PRODUCT_SERVICE_URL}/api/v1/products/{product_id}",
                headers={"X-Service-Key": settings.INTERNAL_SERVICE_KEY},
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "product_id":     product_id,
                    "title":          data.get("title"),
                    "brand":          data.get("brand"),
                    "rsin":           data.get("rsin"),
                    "product_type":   data.get("product_type"),
                    "listing_status": data.get("listing_status"),
                    "price":          data.get("price"),
                    "organisation_id": data.get("organisation_id"),
                }
    except Exception as exc:
        log.warning("verify.product_fetch_failed", product_id=product_id, error=str(exc))
    return None


def compute_geohash(lat: float, lng: float, precision: int = 5) -> str:
    """Simple grid cell for heatmap clustering."""
    return f"{round(lat, precision - 2)},{round(lng, precision - 2)}"

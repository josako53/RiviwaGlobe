"""services/qr_service.py — QR generation, org SMS code resolution, and scan handling."""
from __future__ import annotations

import io
import re
import secrets
import uuid
from datetime import datetime
from typing import Optional

import httpx
import structlog

from core.config import settings
from core.security import generate_short_code

log = structlog.get_logger(__name__)

_ORG_SMS_CACHE: dict[str, str] = {}  # org_id → sms_code, in-memory cache


async def get_org_sms_code(org_id: str) -> str:
    """
    Fetch an org's registered sms_code from auth service.
    Falls back to a sanitised slug prefix if none is set.
    Results are cached per process restart (infrequently changing).
    """
    if org_id in _ORG_SMS_CACHE:
        return _ORG_SMS_CACHE[org_id]

    sms_code = None
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.get(
                f"{settings.AUTH_SERVICE_URL}/api/v1/orgs/{org_id}",
                headers={"X-Service-Key": settings.INTERNAL_SERVICE_KEY},
            )
            if resp.status_code == 200:
                data = resp.json()
                sms_code = data.get("sms_code")
                if not sms_code:
                    # Derive from slug: first alphanumeric segment, max 10 chars
                    slug = data.get("slug", "") or data.get("display_name", "")
                    sms_code = re.sub(r"[^A-Z0-9]", "", slug.upper())[:10] or "RIVIWA"
    except Exception as exc:
        log.warning("qr_service.org_sms_code_failed", org_id=org_id, error=str(exc))
        sms_code = "RIVIWA"

    _ORG_SMS_CACHE[org_id] = sms_code
    return sms_code


def make_qr_png(redirect_url: str) -> bytes:
    """Generate a QR code PNG for the given URL. Returns raw PNG bytes."""
    import qrcode
    from qrcode.image.styledpil import StyledPilImage

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(redirect_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


async def upload_qr_png(png_bytes: bytes, key: str) -> str:
    """Upload a QR PNG to MinIO. Returns the presigned URL."""
    import aiobotocore.session as aio_session

    sess = aio_session.get_session()
    async with sess.create_client(
        "s3",
        endpoint_url=settings.MINIO_ENDPOINT,
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
    ) as s3:
        try:
            await s3.head_bucket(Bucket=settings.QR_BUCKET)
        except Exception:
            await s3.create_bucket(Bucket=settings.QR_BUCKET)
        await s3.put_object(
            Bucket=settings.QR_BUCKET,
            Key=key,
            Body=png_bytes,
            ContentType="image/png",
        )
        url = await s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.QR_BUCKET, "Key": key},
            ExpiresIn=86400 * 365 * 10,
        )
    return url

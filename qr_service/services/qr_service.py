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
    Derive the QR SMS prefix from the org's display_name.
    Rule: uppercase display_name, replace spaces with hyphens, strip other
    non-alphanumeric chars (except hyphens), collapse repeated hyphens.
    Examples:
      "Yas Tanzania"    → YAS-TANZANIA
      "TARURA Test PIU" → TARURA-TEST-PIU
      "CRDB Bank"       → CRDB-BANK
      "MNH"             → MNH
    Falls back to slug-derived prefix, then "RIVIWA" if auth is unreachable.
    Results cached per process lifetime (display_names rarely change).
    """
    if org_id in _ORG_SMS_CACHE:
        return _ORG_SMS_CACHE[org_id]

    prefix = None
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.get(
                f"{settings.AUTH_SERVICE_URL}/api/v1/internal/orgs/{org_id}/sms-code",
                headers={"X-Service-Key": settings.INTERNAL_SERVICE_KEY},
            )
            if resp.status_code == 200:
                data = resp.json()
                raw = data.get("display_name") or data.get("slug") or ""
                # spaces → hyphens, uppercase, strip everything except A-Z 0-9 and -
                prefix = re.sub(r"[^A-Z0-9-]", "", raw.upper().replace(" ", "-"))
                # collapse consecutive hyphens, strip leading/trailing hyphens
                prefix = re.sub(r"-+", "-", prefix).strip("-") or None
    except Exception as exc:
        log.warning("qr_service.org_sms_code_failed", org_id=org_id, error=str(exc))

    if not prefix:
        prefix = "RIVIWA"

    _ORG_SMS_CACHE[org_id] = prefix
    return prefix


def make_qr_png(redirect_url: str) -> bytes:
    """
    Generate a branded QR code PNG.

    Layout:
      ┌─────────────────────────┐
      │                         │
      │       QR modules        │  ← qrcode data (ERROR_CORRECT_M)
      │                         │
      ├─────────────────────────┤  ← 1px separator (#e0e0e0)
      │        Riviwa™          │  ← trademark footer strip (40px)
      └─────────────────────────┘

    The Riviwa™ text is rendered below the QR data area so it never
    interferes with scan reliability. Pillow draws the footer using
    DejaVuSans-Bold (installed in the Docker image) with a graceful
    fallback to PIL's built-in bitmap font.
    """
    import qrcode
    from PIL import Image, ImageDraw, ImageFont

    # ── 1. Build the QR matrix ────────────────────────────────────────────────
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(redirect_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="#1a1a2e", back_color="white").convert("RGB")

    qr_w, qr_h = qr_img.size
    footer_h = max(44, qr_w // 7)   # proportional — taller QR gets taller footer

    # ── 2. Create canvas: QR on top, white footer below ───────────────────────
    canvas = Image.new("RGB", (qr_w, qr_h + footer_h), "white")
    canvas.paste(qr_img, (0, 0))

    draw = ImageDraw.Draw(canvas)

    # Subtle separator line between QR and footer
    draw.line([(0, qr_h), (qr_w, qr_h)], fill="#e0e0e0", width=1)

    # ── 3. Load font ──────────────────────────────────────────────────────────
    import os as _os
    font_size = max(20, footer_h // 2)
    font = None
    _here = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    for font_path in [
        _os.path.join(_here, "assets", "DejaVuSans-Bold.ttf"),   # bundled (persists via bind mount)
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    ]:
        try:
            font = ImageFont.truetype(font_path, font_size)
            break
        except (IOError, OSError):
            continue
    if font is None:
        font = ImageFont.load_default()

    # ── 4. Draw "Riviwa™" centered in the footer ──────────────────────────────
    brand_text = "Riviwa™"   # ™ = U+2122
    bbox = draw.textbbox((0, 0), brand_text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    text_x = (qr_w - text_w) // 2
    text_y = qr_h + (footer_h - text_h) // 2

    draw.text((text_x, text_y), brand_text, fill="#1a1a2e", font=font)

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
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

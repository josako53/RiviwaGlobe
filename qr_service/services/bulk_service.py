"""services/bulk_service.py — Background bulk QR generation and ZIP packaging."""
from __future__ import annotations

import io
import uuid
import zipfile
from datetime import datetime
from typing import Optional

import structlog

from core.config import settings
from core.security import generate_short_code
from services.qr_service import get_org_sms_code, make_qr_png, upload_qr_png

log = structlog.get_logger(__name__)


async def run_bulk_job(
    batch_id: uuid.UUID,
    organisation_id: uuid.UUID,
    qr_type: str,
    count: int,
    label: Optional[str] = None,
    product_id: Optional[uuid.UUID] = None,
    title: str = "",
    brand: str = "",
    rsin: str = "",
) -> None:
    """
    Generate `count` QR codes for a product, package all PNGs into a ZIP,
    upload to MinIO, and update the QRBatch row.
    Runs as a FastAPI background task — exceptions are logged, not raised.
    """
    from db.session import AsyncSessionLocal
    from models.qr import QRBatch, QRCode
    from repositories.qr_repo import QRRepository

    log.info("bulk_service.start", batch_id=str(batch_id), count=count)

    async with AsyncSessionLocal() as db:
        repo = QRRepository(db)
        batch = await repo.get_batch(batch_id)
        if not batch:
            log.error("bulk_service.batch_not_found", batch_id=str(batch_id))
            return

        try:
            await repo.update_batch(batch, status="GENERATING")
            await db.commit()

            org_id_str = str(organisation_id)
            org_sms_code = await get_org_sms_code(org_id_str)

            zip_buf = io.BytesIO()
            generated = 0

            with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                for i in range(count):
                    short_code = generate_short_code(8)
                    sms_code   = f"{org_sms_code}-{short_code}"
                    redirect   = f"{settings.FEEDBACK_APP_URL}/feedback?qr={short_code}"

                    # Generate PNG
                    try:
                        png = make_qr_png(redirect)
                    except Exception as exc:
                        log.warning("bulk_service.png_failed", i=i, error=str(exc))
                        continue

                    # Upload individual PNG to MinIO
                    png_key = f"qr-codes/{org_id_str}/{short_code}.png"
                    try:
                        png_url = await upload_qr_png(png, png_key)
                    except Exception as exc:
                        log.warning("bulk_service.upload_failed", i=i, error=str(exc))
                        png_url = ""

                    # Save QR code to DB
                    qr = QRCode(
                        short_code=short_code,
                        sms_code=sms_code,
                        org_sms_code=org_sms_code,
                        qr_type=qr_type.upper(),
                        organisation_id=organisation_id,
                        product_id=product_id,
                        batch_id=batch_id,
                        redirect_url=redirect,
                        qr_image_key=png_key,
                        qr_image_url=png_url,
                    )
                    db.add(qr)

                    # Add to ZIP — filename encodes RSIN + short_code for traceability
                    fn = f"{rsin}_{short_code}.png" if rsin else f"{short_code}.png"
                    zf.writestr(fn, png)
                    generated += 1

            await db.flush()

            # Upload ZIP
            zip_bytes = zip_buf.getvalue()
            zip_key = f"batches/{org_id_str}/{batch_id}.zip"
            try:
                zip_url = await upload_qr_png(zip_bytes, zip_key)
            except Exception as exc:
                log.warning("bulk_service.zip_upload_failed", error=str(exc))
                zip_url = ""

            await repo.update_batch(
                batch,
                status="READY",
                generated_count=generated,
                zip_key=zip_key,
                zip_url=zip_url,
                completed_at=datetime.utcnow(),
            )
            await db.commit()
            log.info("bulk_service.done", batch_id=str(batch_id), generated=generated)

        except Exception as exc:
            log.error("bulk_service.failed", batch_id=str(batch_id), error=str(exc))
            try:
                await repo.update_batch(batch, status="FAILED", error_message=str(exc)[:1024])
                await db.commit()
            except Exception:
                pass

"""api/v1/qr.py — QR code management endpoints (authenticated)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import InternalDep, JWTDep
from core.security import generate_short_code
from db.session import get_async_session
from models.qr import QRBatch, QRCode
from repositories.qr_repo import QRRepository
from services.bulk_service import run_bulk_job
from services.qr_service import get_org_sms_code, make_qr_png, upload_qr_png

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/qr", tags=["QR Codes"])


def _qr_out(q: QRCode) -> dict:
    return {
        "id":               str(q.id),
        "short_code":       q.short_code,
        "sms_code":         q.sms_code,
        "qr_type":          q.qr_type,
        "organisation_id":  str(q.organisation_id),
        "project_id":       str(q.project_id)  if q.project_id  else None,
        "service_id":       str(q.service_id)  if q.service_id  else None,
        "product_id":       str(q.product_id)  if q.product_id  else None,
        "qr_image_url":     q.qr_image_url,
        "redirect_url":     q.redirect_url,
        "scan_count":       q.scan_count,
        "is_active":        q.is_active,
        "batch_id":         str(q.batch_id) if q.batch_id else None,
        "expires_at":       q.expires_at.isoformat() if q.expires_at else None,
        "created_at":       q.created_at.isoformat(),
    }


@router.post("/generate", status_code=status.HTTP_201_CREATED)
async def generate_qr(
    body: dict,
    bg: BackgroundTasks,
    db: AsyncSession = Depends(get_async_session),
    _claims=JWTDep,
) -> dict:
    """
    Generate a single QR code (LOCATION, SERVICE, PRODUCT, RECEIPT).
    Returns immediately with short_code and redirect_url.
    The QR PNG is uploaded to MinIO as a background task.
    """
    qr_type        = (body.get("qr_type") or "LOCATION").upper()
    organisation_id = uuid.UUID(body["organisation_id"])

    short_code   = generate_short_code(8)
    org_sms_code = await get_org_sms_code(str(organisation_id))
    sms_code     = f"{org_sms_code}-{short_code}"
    redirect_url = f"{body.get('redirect_url', '')}".strip() or \
                   f"https://app.riviwa.com/feedback?qr={short_code}"

    qr = QRCode(
        short_code=short_code,
        sms_code=sms_code,
        org_sms_code=org_sms_code,
        qr_type=qr_type,
        organisation_id=organisation_id,
        product_id=uuid.UUID(body["product_id"])   if body.get("product_id")   else None,
        project_id=uuid.UUID(body["project_id"])   if body.get("project_id")   else None,
        service_id=uuid.UUID(body["service_id"])   if body.get("service_id")   else None,
        redirect_url=redirect_url,
    )

    repo = QRRepository(db)
    qr = await repo.create(qr)
    await db.commit()
    await db.refresh(qr)

    # Generate and upload PNG in background
    bg.add_task(_generate_and_upload_png, str(qr.id), short_code, redirect_url, str(organisation_id))
    log.info("qr.generated", short_code=short_code, qr_type=qr_type, org=str(organisation_id))
    return _qr_out(qr)


async def _generate_and_upload_png(qr_id: str, short_code: str, redirect_url: str, org_id: str) -> None:
    from db.session import AsyncSessionLocal
    try:
        png = make_qr_png(redirect_url)
        key = f"qr-codes/{org_id}/{short_code}.png"
        url = await upload_qr_png(png, key)
        async with AsyncSessionLocal() as db:
            from sqlalchemy import update as sa_update
            await db.execute(
                sa_update(QRCode).where(QRCode.id == uuid.UUID(qr_id))
                .values(qr_image_key=key, qr_image_url=url, updated_at=datetime.utcnow())
            )
            await db.commit()
    except Exception as exc:
        log.warning("qr.png_bg_failed", qr_id=qr_id, error=str(exc))


@router.get("", status_code=200)
async def list_qr_codes(
    organisation_id: uuid.UUID,
    qr_type: Optional[str] = None,
    page: int = 1,
    size: int = 20,
    db: AsyncSession = Depends(get_async_session),
    _claims=JWTDep,
) -> dict:
    repo = QRRepository(db)
    items, total = await repo.list_by_org(organisation_id, qr_type, page, size)
    return {"total": total, "page": page, "size": size, "items": [_qr_out(q) for q in items]}


@router.get("/analytics/scans", status_code=200)
async def get_scan_analytics(
    organisation_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
    _claims=JWTDep,
) -> dict:
    repo = QRRepository(db)
    return await repo.scan_analytics(organisation_id)


@router.get("/bulk/{batch_id}", status_code=200)
async def get_batch_status(
    batch_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
    _claims=JWTDep,
) -> dict:
    repo = QRRepository(db)
    batch = await repo.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail={"error": "BATCH_NOT_FOUND"})
    return {
        "batch_id":        str(batch.id),
        "organisation_id": str(batch.organisation_id),
        "qr_type":         batch.qr_type,
        "count":           batch.count,
        "status":          batch.status,
        "generated_count": batch.generated_count,
        "zip_url":         batch.zip_url,
        "error_message":   batch.error_message,
        "created_at":      batch.created_at.isoformat(),
        "completed_at":    batch.completed_at.isoformat() if batch.completed_at else None,
    }


@router.post("/bulk", status_code=status.HTTP_202_ACCEPTED)
async def create_bulk_batch(
    body: dict,
    bg: BackgroundTasks,
    db: AsyncSession = Depends(get_async_session),
    _claims=JWTDep,
) -> dict:
    """
    Queue a bulk QR generation job for a product. Returns immediately with batch_id.
    The job generates `count` QR PNGs and packages them into a ZIP in the background.
    """
    organisation_id = uuid.UUID(body["organisation_id"])
    count           = int(body.get("count", 1))
    qr_type         = (body.get("qr_type") or "PRODUCT").upper()

    if not 1 <= count <= 10000:
        raise HTTPException(status_code=422, detail={"error": "count must be 1–10000"})

    batch = QRBatch(
        organisation_id=organisation_id,
        qr_type=qr_type,
        count=count,
        label=body.get("label"),
        title=body.get("title", ""),
        brand=body.get("brand", ""),
        rsin=body.get("rsin", ""),
        product_id=uuid.UUID(body["product_id"]) if body.get("product_id") else None,
        status="PENDING",
    )
    repo = QRRepository(db)
    batch = await repo.create_batch(batch)
    await db.commit()
    await db.refresh(batch)

    bg.add_task(
        run_bulk_job,
        batch.id,
        organisation_id,
        qr_type,
        count,
        body.get("label"),
        batch.product_id,
        body.get("title", ""),
        body.get("brand", ""),
        body.get("rsin", ""),
    )

    log.info("qr.bulk_queued", batch_id=str(batch.id), count=count, org=str(organisation_id))
    return {
        "batch_id":        str(batch.id),
        "organisation_id": str(organisation_id),
        "qr_type":         qr_type,
        "count":           count,
        "status":          "PENDING",
        "message":         f"Bulk generation queued. Poll GET /api/v1/qr/bulk/{batch.id} for status.",
    }


@router.get("/{qr_id}", status_code=200)
async def get_qr_code(
    qr_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
    _claims=JWTDep,
) -> dict:
    repo = QRRepository(db)
    qr = await repo.get_by_id(qr_id)
    if not qr or not qr.is_active:
        raise HTTPException(status_code=404, detail={"error": "QR_NOT_FOUND"})
    return _qr_out(qr)


@router.delete("/{qr_id}", status_code=200)
async def deactivate_qr_code(
    qr_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
    _claims=JWTDep,
) -> dict:
    repo = QRRepository(db)
    qr = await repo.get_by_id(qr_id)
    if not qr:
        raise HTTPException(status_code=404, detail={"error": "QR_NOT_FOUND"})
    await repo.deactivate(qr)
    await db.commit()
    return {"message": "QR code deactivated.", "short_code": qr.short_code}

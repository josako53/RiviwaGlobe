"""api/v1/qr.py — QR code management endpoints (authenticated)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import JWTDep
from core.security import generate_short_code
from db.session import get_async_session
from models.qr import QRBatch, QRCode
from repositories.qr_repo import QRRepository
from services.bulk_service import run_bulk_job
from services.qr_service import get_org_sms_code, make_qr_png, upload_qr_png

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/qr", tags=["QR Codes"])


# ── Serialisers ───────────────────────────────────────────────────────────────

def _qr_out(q: QRCode) -> dict:
    return {
        "id":               str(q.id),
        "short_code":       q.short_code,
        "sms_code":         q.sms_code,
        "qr_type":          q.qr_type,
        "organisation_id":  str(q.organisation_id),
        "project_id":       str(q.project_id)      if q.project_id      else None,
        "service_id":       str(q.service_id)      if q.service_id      else None,
        "product_id":       str(q.product_id)      if q.product_id      else None,
        "branch_id":        str(q.branch_id)       if q.branch_id       else None,
        "department_id":    str(q.department_id)   if q.department_id   else None,
        "label":            q.label,
        "qr_image_url":     q.qr_image_url,
        "redirect_url":     q.redirect_url,
        "scan_count":       q.scan_count,
        "is_active":        q.is_active,
        "batch_id":         str(q.batch_id) if q.batch_id else None,
        "expires_at":       q.expires_at.isoformat() if q.expires_at else None,
        "created_at":       q.created_at.isoformat(),
        "updated_at":       q.updated_at.isoformat(),
    }


def _batch_out(b: QRBatch) -> dict:
    return {
        "batch_id":        str(b.id),
        "organisation_id": str(b.organisation_id),
        "product_id":      str(b.product_id) if b.product_id else None,
        "qr_type":         b.qr_type,
        "count":           b.count,
        "label":           b.label,
        "status":          b.status,
        "generated_count": b.generated_count,
        "zip_url":         b.zip_url,
        "error_message":   b.error_message,
        "created_at":      b.created_at.isoformat(),
        "completed_at":    b.completed_at.isoformat() if b.completed_at else None,
    }


# ── Generate single QR ────────────────────────────────────────────────────────

@router.post("/generate", status_code=status.HTTP_201_CREATED,
             summary="Generate a single QR code")
async def generate_qr(
    body: dict,
    bg:   BackgroundTasks,
    db:   AsyncSession = Depends(get_async_session),
    _claims=JWTDep,
) -> dict:
    """
    Generate a single QR code (LOCATION, SERVICE, PRODUCT, RECEIPT).

    Returns immediately with `short_code` and `redirect_url`.
    The QR PNG is uploaded to MinIO as a background task — poll
    `GET /qr/{id}` for `qr_image_url` once it appears.

    Optional context links (soft FKs, cross-service):
    `product_id`, `service_id`, `project_id`, `branch_id`, `department_id`
    """
    qr_type         = (body.get("qr_type") or "LOCATION").upper()
    organisation_id = uuid.UUID(body["organisation_id"])

    short_code   = generate_short_code(8)
    org_sms_code = await get_org_sms_code(str(organisation_id))
    sms_code     = f"{org_sms_code}-{short_code}"
    redirect_url = (body.get("redirect_url") or "").strip() or \
                   f"https://app.riviwa.com/feedback?qr={short_code}"

    qr = QRCode(
        short_code=short_code,
        sms_code=sms_code,
        org_sms_code=org_sms_code,
        qr_type=qr_type,
        organisation_id=organisation_id,
        product_id=    uuid.UUID(body["product_id"])    if body.get("product_id")    else None,
        project_id=    uuid.UUID(body["project_id"])    if body.get("project_id")    else None,
        service_id=    uuid.UUID(body["service_id"])    if body.get("service_id")    else None,
        branch_id=     uuid.UUID(body["branch_id"])     if body.get("branch_id")     else None,
        department_id= uuid.UUID(body["department_id"]) if body.get("department_id") else None,
        label=         body.get("label"),
        redirect_url=  redirect_url,
    )

    repo = QRRepository(db)
    qr   = await repo.create(qr)
    await db.commit()
    await db.refresh(qr)

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


# ── List QR codes (with all filters) ─────────────────────────────────────────

@router.get("", status_code=200,
            summary="List QR codes — filter by product, service, branch, department, project, type")
async def list_qr_codes(
    organisation_id: uuid.UUID,
    qr_type:         Optional[str]       = Query(default=None, description="LOCATION | SERVICE | PRODUCT | RECEIPT"),
    product_id:      Optional[uuid.UUID] = Query(default=None, description="Filter by product"),
    service_id:      Optional[uuid.UUID] = Query(default=None, description="Filter by service"),
    project_id:      Optional[uuid.UUID] = Query(default=None, description="Filter by project"),
    branch_id:       Optional[uuid.UUID] = Query(default=None, description="Filter by branch / location"),
    department_id:   Optional[uuid.UUID] = Query(default=None, description="Filter by department"),
    batch_id:        Optional[uuid.UUID] = Query(default=None, description="Filter by bulk batch"),
    is_active:       Optional[bool]      = Query(default=True,  description="true=active only (default), false=deactivated, omit=all"),
    page:            int = Query(default=1, ge=1),
    size:            int = Query(default=20, ge=1, le=100),
    db:              AsyncSession = Depends(get_async_session),
    _claims=JWTDep,
) -> dict:
    repo = QRRepository(db)
    items, total = await repo.list_by_org(
        org_id=organisation_id,
        qr_type=qr_type,
        product_id=product_id,
        service_id=service_id,
        project_id=project_id,
        branch_id=branch_id,
        department_id=department_id,
        batch_id=batch_id,
        is_active=is_active,
        page=page,
        size=size,
    )
    return {"total": total, "page": page, "size": size, "items": [_qr_out(q) for q in items]}


# ── Org-level scan analytics ──────────────────────────────────────────────────

@router.get("/analytics/scans", status_code=200,
            summary="Org-wide scan analytics — totals, unique scanners, conversion rate")
async def get_scan_analytics(
    organisation_id: uuid.UUID,
    db:              AsyncSession = Depends(get_async_session),
    _claims=JWTDep,
) -> dict:
    repo = QRRepository(db)
    return await repo.scan_analytics(organisation_id)


# ── List bulk batches ─────────────────────────────────────────────────────────
# MUST come before /bulk/{batch_id} to avoid route shadowing

@router.get("/bulk", status_code=200,
            summary="List bulk generation batches for an org")
async def list_batches(
    organisation_id: uuid.UUID,
    qr_type:         Optional[str] = Query(default=None, description="PRODUCT | LOCATION | SERVICE"),
    status:          Optional[str] = Query(default=None, description="PENDING | GENERATING | READY | FAILED"),
    page:            int = Query(default=1, ge=1),
    size:            int = Query(default=20, ge=1, le=100),
    db:              AsyncSession = Depends(get_async_session),
    _claims=JWTDep,
) -> dict:
    repo = QRRepository(db)
    items, total = await repo.list_batches(
        org_id=organisation_id, qr_type=qr_type, status=status, page=page, size=size,
    )
    return {"total": total, "page": page, "size": size, "items": [_batch_out(b) for b in items]}


# ── Single batch status ───────────────────────────────────────────────────────

@router.get("/bulk/{batch_id}", status_code=200,
            summary="Get bulk generation batch status and ZIP download URL")
async def get_batch_status(
    batch_id: uuid.UUID,
    db:       AsyncSession = Depends(get_async_session),
    _claims=JWTDep,
) -> dict:
    repo = QRRepository(db)
    batch = await repo.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail={"error": "BATCH_NOT_FOUND"})
    return _batch_out(batch)


# ── Queue bulk generation ─────────────────────────────────────────────────────

@router.post("/bulk", status_code=status.HTTP_202_ACCEPTED,
             summary="Queue a bulk QR generation job (1–10,000 codes)")
async def create_bulk_batch(
    body: dict,
    bg:   BackgroundTasks,
    db:   AsyncSession = Depends(get_async_session),
    _claims=JWTDep,
) -> dict:
    """
    Queue a bulk QR generation job. Returns immediately with `batch_id`.
    Poll `GET /qr/bulk/{batch_id}` for status. When `status=READY`,
    `zip_url` contains a presigned MinIO URL to download the ZIP of PNGs.
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
    repo  = QRRepository(db)
    batch = await repo.create_batch(batch)
    await db.commit()
    await db.refresh(batch)

    bg.add_task(
        run_bulk_job, batch.id, organisation_id, qr_type, count,
        body.get("label"), batch.product_id,
        body.get("title", ""), body.get("brand", ""), body.get("rsin", ""),
    )
    log.info("qr.bulk_queued", batch_id=str(batch.id), count=count, org=str(organisation_id))
    return {
        **_batch_out(batch),
        "message": f"Bulk generation queued. Poll GET /api/v1/qr/bulk/{batch.id} for status.",
    }


# ── Receipt sessions ──────────────────────────────────────────────────────────
# MUST come before /{qr_id} to avoid route shadowing

@router.get("/receipt-sessions", status_code=200,
            summary="List receipt sessions for an org")
async def list_receipt_sessions(
    organisation_id: uuid.UUID,
    is_consumed:     Optional[bool] = Query(default=None, description="true=feedback submitted, false=pending, omit=all"),
    page:            int = Query(default=1, ge=1),
    size:            int = Query(default=20, ge=1, le=100),
    db:              AsyncSession = Depends(get_async_session),
    _claims=JWTDep,
) -> dict:
    repo = QRRepository(db)
    items, total = await repo.list_receipt_sessions(
        org_id=organisation_id, is_consumed=is_consumed, page=page, size=size,
    )
    return {
        "total": total, "page": page, "size": size,
        "items": [
            {
                "id":                   str(s.id),
                "organisation_id":      str(s.organisation_id),
                "consumer_name":        s.consumer_name,
                "consumer_phone":       s.consumer_phone,
                "service_name":         s.service_name,
                "department":           s.department,
                "attendant_name":       s.attendant_name,
                "location":             s.location,
                "receipt_number":       s.receipt_number,
                "amount":               s.amount,
                "currency":             s.currency,
                "transaction_datetime": s.transaction_datetime,
                "is_consumed":          s.is_consumed,
                "created_at":           s.created_at.isoformat(),
            }
            for s in items
        ],
    }


# ── Single QR code ────────────────────────────────────────────────────────────

@router.get("/{qr_id}", status_code=200,
            summary="Get a single QR code by ID")
async def get_qr_code(
    qr_id: uuid.UUID,
    db:    AsyncSession = Depends(get_async_session),
    _claims=JWTDep,
) -> dict:
    repo = QRRepository(db)
    qr   = await repo.get_by_id(qr_id)
    if not qr:
        raise HTTPException(status_code=404, detail={"error": "QR_NOT_FOUND"})
    return _qr_out(qr)


# ── Per-QR scan list ──────────────────────────────────────────────────────────

@router.get("/{qr_id}/scans", status_code=200,
            summary="List individual scan records for a QR code")
async def list_qr_scans(
    qr_id:              uuid.UUID,
    feedback_submitted: Optional[bool] = Query(default=None, description="true=converted, false=not yet, omit=all"),
    page:               int = Query(default=1, ge=1),
    size:               int = Query(default=20, ge=1, le=100),
    db:                 AsyncSession = Depends(get_async_session),
    _claims=JWTDep,
) -> dict:
    repo   = QRRepository(db)
    qr     = await repo.get_by_id(qr_id)
    if not qr:
        raise HTTPException(status_code=404, detail={"error": "QR_NOT_FOUND"})
    items, total = await repo.list_scans(
        qr_id=qr_id, feedback_submitted=feedback_submitted, page=page, size=size,
    )
    return {
        "qr_id": str(qr_id),
        "total": total, "page": page, "size": size,
        "items": [
            {
                "id":                 str(s.id),
                "scanner_ip":         s.scanner_ip,
                "scanner_ua":         s.scanner_ua,
                "fingerprint":        s.fingerprint,
                "feedback_submitted": s.feedback_submitted,
                "feedback_id":        str(s.feedback_id) if s.feedback_id else None,
                "scanned_at":         s.scanned_at.isoformat(),
            }
            for s in items
        ],
    }


# ── Per-QR analytics ──────────────────────────────────────────────────────────

@router.get("/{qr_id}/analytics", status_code=200,
            summary="Scan analytics for a single QR code")
async def get_qr_analytics(
    qr_id: uuid.UUID,
    db:    AsyncSession = Depends(get_async_session),
    _claims=JWTDep,
) -> dict:
    repo = QRRepository(db)
    qr   = await repo.get_by_id(qr_id)
    if not qr:
        raise HTTPException(status_code=404, detail={"error": "QR_NOT_FOUND"})
    stats = await repo.scan_analytics_for_qr(qr_id)
    return {"qr_id": str(qr_id), "short_code": qr.short_code, **stats}


# ── Update QR code ────────────────────────────────────────────────────────────

@router.patch("/{qr_id}", status_code=200,
              summary="Update a QR code — redirect URL, entity links, label, active state")
async def update_qr_code(
    qr_id: uuid.UUID,
    body:  dict,
    db:    AsyncSession = Depends(get_async_session),
    _claims=JWTDep,
) -> dict:
    """
    Updatable fields: `redirect_url`, `product_id`, `service_id`, `project_id`,
    `branch_id`, `department_id`, `label`, `is_active`.

    All fields are optional — send only what you want to change.
    Unknown fields are silently ignored.
    """
    repo = QRRepository(db)
    qr   = await repo.get_by_id(qr_id)
    if not qr:
        raise HTTPException(status_code=404, detail={"error": "QR_NOT_FOUND"})

    # Cast UUID string fields to UUID objects
    for uuid_field in ("product_id", "service_id", "project_id", "branch_id", "department_id"):
        if uuid_field in body and body[uuid_field] is not None:
            body[uuid_field] = uuid.UUID(str(body[uuid_field]))
        elif uuid_field in body and body[uuid_field] is None:
            pass  # explicit null → clear the FK

    qr = await repo.update_qr(qr, **body)
    await db.commit()
    await db.refresh(qr)
    return _qr_out(qr)


# ── Deactivate QR code ────────────────────────────────────────────────────────

@router.delete("/{qr_id}", status_code=200,
               summary="Deactivate a QR code (soft delete)")
async def deactivate_qr_code(
    qr_id: uuid.UUID,
    db:    AsyncSession = Depends(get_async_session),
    _claims=JWTDep,
) -> dict:
    repo = QRRepository(db)
    qr   = await repo.get_by_id(qr_id)
    if not qr:
        raise HTTPException(status_code=404, detail={"error": "QR_NOT_FOUND"})
    await repo.deactivate(qr)
    await db.commit()
    return {"message": "QR code deactivated.", "short_code": qr.short_code}

"""api/v1/internal.py — Internal service-to-service QR endpoints."""
from __future__ import annotations

import secrets
import uuid
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import InternalDep
from core.config import settings
from core.security import generate_short_code
from db.session import get_async_session
from models.qr import QRCode, QRScan, ReceiptSession
from repositories.qr_repo import QRRepository
from services.qr_service import get_org_sms_code, make_qr_png, upload_qr_png

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/internal/qr", tags=["QR — Internal"])


@router.post("/receipt", status_code=201)
async def create_receipt_qr(
    body: dict,
    db: AsyncSession = Depends(get_async_session),
    _=InternalDep,
) -> dict:
    """
    Generate a receipt QR + session for a third-party transaction.
    Called by integration_service when a partner pushes a receipt.

    Returns short_code (for QR), sms_code ({ORG_CODE}-{SHORT_CODE}),
    session_token (for direct feedback submission), and qr_image_url.
    """
    organisation_id = uuid.UUID(body["organisation_id"])
    org_id_str      = str(organisation_id)
    org_sms_code    = await get_org_sms_code(org_id_str)

    short_code   = generate_short_code(8)
    sms_code     = f"{org_sms_code}-{short_code}"
    session_token = secrets.token_urlsafe(32)

    # Create receipt session
    session = ReceiptSession(
        organisation_id=organisation_id,
        consumer_phone=body.get("consumer_phone"),
        consumer_name=body.get("consumer_name"),
        service_name=body.get("service_name"),
        department=body.get("department"),
        attendant_name=body.get("attendant_name"),
        location=body.get("location"),
        transaction_datetime=body.get("transaction_datetime"),
        receipt_number=body.get("receipt_number"),
        amount=body.get("amount"),
        currency=body.get("currency"),
        custom_attributes=body.get("custom_attributes"),
    )
    repo = QRRepository(db)
    session = await repo.create_receipt_session(session)

    redirect_url = (
        f"{settings.FEEDBACK_APP_URL}/feedback"
        f"?qr={short_code}&session={session_token}"
    )

    # Upload QR image (sync in handler — receipts are low volume)
    qr_image_url = qr_image_key = None
    try:
        png = make_qr_png(redirect_url)
        key = f"qr-codes/{org_id_str}/{short_code}.png"
        qr_image_url = await upload_qr_png(png, key)
        qr_image_key = key
    except Exception as exc:
        log.warning("internal.receipt_qr.png_failed", error=str(exc))

    qr = QRCode(
        short_code=short_code,
        sms_code=sms_code,
        org_sms_code=org_sms_code,
        qr_type="RECEIPT",
        organisation_id=organisation_id,
        receipt_session_id=session.id,
        redirect_url=redirect_url,
        qr_image_key=qr_image_key,
        qr_image_url=qr_image_url,
    )
    await repo.create(qr)
    await db.commit()

    log.info("internal.receipt_qr.created", short_code=short_code, session=str(session.id))
    return {
        "short_code":         short_code,
        "sms_code":           sms_code,
        "org_sms_code":       org_sms_code,
        "qr_image_url":       qr_image_url,
        "qr_redirect_url":    f"{settings.FEEDBACK_APP_URL}/qr/{short_code}",
        "redirect_url":       redirect_url,
        "session_token":      session_token,
        "receipt_session_id": str(session.id),
        "sms_instructions": (
            f"Text '{sms_code}' to {settings.SMS_SHORT_NUMBER} "
            f"or reply '{short_code}' if already in conversation."
        ),
    }


@router.get("/lookup", status_code=200)
async def lookup_code(
    short_code: str,
    db: AsyncSession = Depends(get_async_session),
    _=InternalDep,
) -> dict:
    """
    Look up a QR/SMS code. Accepts any format:
      - XXXXXX                  (bare short code)
      - UTT-XXXXXX              (org-prefixed SMS code)
      - UTT XXXXXX              (space-separated text from SMS)

    Returns code details + feedback_already_submitted flag.
    Called by verification_service to check code authenticity.
    """
    repo = QRRepository(db)
    qr = await repo.resolve(short_code)
    if not qr or not qr.is_active:
        raise HTTPException(status_code=404, detail={"error": "CODE_NOT_FOUND"})

    already_submitted, feedback_id = await repo.has_feedback(
        qr.id, qr.receipt_session_id
    )

    return {
        "qr_code_id":              str(qr.id),
        "short_code":              qr.short_code,
        "sms_code":                qr.sms_code,
        "org_sms_code":            qr.org_sms_code,
        "qr_type":                 qr.qr_type,
        "organisation_id":         str(qr.organisation_id),
        "product_id":              str(qr.product_id)  if qr.product_id  else None,
        "project_id":              str(qr.project_id)  if qr.project_id  else None,
        "service_id":              str(qr.service_id)  if qr.service_id  else None,
        "receipt_session_id":      str(qr.receipt_session_id) if qr.receipt_session_id else None,
        "is_active":               qr.is_active,
        "redirect_url":            qr.redirect_url,
        "feedback_already_submitted": already_submitted,
        "feedback_id":             str(feedback_id) if feedback_id else None,
        "scan_count":              qr.scan_count,
    }


@router.post("/mark-feedback", status_code=200)
async def mark_feedback(
    body: dict,
    db: AsyncSession = Depends(get_async_session),
    _=InternalDep,
) -> dict:
    """
    Mark a QR/SMS code as having feedback submitted.
    Called by the feedback_service Kafka consumer or directly for testing.

    Body:
      short_code   — any resolvable format (bare, org-prefixed, SMS text)
      feedback_id  — optional UUID of the feedback record
    """
    repo = QRRepository(db)
    short_code  = body.get("short_code", "")
    feedback_id = uuid.UUID(body["feedback_id"]) if body.get("feedback_id") else None

    ok = await repo.mark_feedback(short_code, feedback_id)
    if not ok:
        raise HTTPException(status_code=404, detail={"error": "CODE_NOT_FOUND"})
    await db.commit()
    return {"marked": True, "short_code": short_code}


@router.get("/receipt-session/{session_id}", status_code=200)
async def get_receipt_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
    _=InternalDep,
) -> dict:
    """Return receipt session details for verification_service ALREADY_USED response."""
    repo = QRRepository(db)
    session = await repo.get_receipt_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail={"error": "SESSION_NOT_FOUND"})
    return {
        "id":                   str(session.id),
        "organisation_id":      str(session.organisation_id),
        "consumer_name":        session.consumer_name,
        "service_name":         session.service_name,
        "department":           session.department,
        "attendant_name":       session.attendant_name,
        "location":             session.location,
        "transaction_datetime": session.transaction_datetime,
        "receipt_number":       session.receipt_number,
        "amount":               session.amount,
        "currency":             session.currency,
        "custom_attributes":    session.custom_attributes,
        "is_consumed":          session.is_consumed,
    }


@router.post("/increment-scan", status_code=200)
async def increment_scan(
    body: dict,
    db: AsyncSession = Depends(get_async_session),
    _=InternalDep,
) -> dict:
    """
    Record a scan event and increment scan_count on the QR code.
    Called by verification_service immediately after a successful code lookup.

    Body: {qr_code_id, short_code, scanner_ip?, user_agent?}
    """
    from sqlalchemy import select as sa_select
    qr_id = uuid.UUID(body["qr_code_id"])
    short_code = body.get("short_code", "")
    repo = QRRepository(db)

    # Fetch QR to get organisation_id and qr_type (required by qr_scans table)
    qr_row = (await db.execute(
        sa_select(QRCode).where(QRCode.id == qr_id)
    )).scalar_one_or_none()
    if not qr_row:
        raise HTTPException(status_code=404, detail={"error": "QR_NOT_FOUND"})

    await repo.increment_scan(qr_id)

    await repo.record_scan(
        qr_id=qr_id,
        short_code=short_code,
        organisation_id=qr_row.organisation_id,
        qr_type=qr_row.qr_type,
        ip=body.get("scanner_ip"),
        ua=body.get("user_agent"),
    )
    await db.commit()
    log.info("internal.qr.scan_recorded", qr_id=str(qr_id), short_code=short_code)
    return {"recorded": True, "qr_code_id": str(qr_id)}

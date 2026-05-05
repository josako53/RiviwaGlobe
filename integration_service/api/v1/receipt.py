"""
api/v1/receipt.py — Real-time receipt/transaction context push.

Third-party partners call this endpoint whenever a transaction occurs
(bus fare, grocery, hospital bill, etc.). Riviwa generates:
  - A unique QR code image (embed in digital or printed receipt)
  - A short SMS code (print at bottom of receipt for feature phone users)
  - A session token (for direct web redirect with pre-filled context)

Flow:
  1. Partner POS/backend → POST /integration/receipt
  2. integration_service stores receipt_transactions row
  3. Calls qr_service to generate QR + short code
  4. Returns all codes to partner for embedding in receipt
"""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import IntegrationAuthDep, AuthContext
from core.config import settings
from db.session import get_async_session
from models.integration import IntegrationClient, ReceiptTransaction

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/integration/receipt", tags=["Integration — Receipt & Transaction"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def push_receipt(
    body: dict,
    db: AsyncSession = Depends(get_async_session),
    ctx: AuthContext = IntegrationAuthDep,
) -> dict:
    """
    Push a receipt/transaction context. Returns a QR code, unique SMS code,
    and session token for the Riviwa feedback widget.

    Required scope: receipt:push

    Body fields:
      consumer_phone      — E.164 phone number
      consumer_name       — Full name
      consumer_email      — Email address
      service_name        — Name of service (e.g. "Bus Fare", "Groceries", "Consultation")
      department          — Department or counter (e.g. "Pharmacy", "Checkout Lane 3")
      attendant_name      — Name of staff who served the customer
      location            — Physical location (branch name, address)
      transaction_datetime — ISO8601 datetime of the transaction
      receipt_number      — Unique receipt/transaction ID from partner system
      amount              — Transaction amount
      currency            — ISO 4217 currency code (e.g. "TZS", "KES")
      custom_attributes   — Any additional key-value pairs (seat number, route, etc.)
      org_id              — Must match client's bound organisation_id if provided
    """
    ctx.require_scope("receipt:push")
    org_id = ctx.validate_org(uuid.UUID(body["org_id"]) if body.get("org_id") else None)

    # Validate: need at least one consumer identifier or a receipt_number
    has_consumer = any(body.get(f) for f in ("consumer_phone", "consumer_name", "consumer_email"))
    if not has_consumer and not body.get("receipt_number"):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "MISSING_CONTEXT",
                "message": "Provide at least one of: consumer_phone, consumer_name, consumer_email, or receipt_number",
            },
        )

    # Store receipt transaction
    session_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(session_token.encode()).hexdigest()

    txn = ReceiptTransaction(
        client_id=ctx.client.id,
        organisation_id=org_id,
        consumer_phone=body.get("consumer_phone"),
        consumer_name=body.get("consumer_name"),
        consumer_email=body.get("consumer_email"),
        service_name=body.get("service_name"),
        department=body.get("department"),
        attendant_name=body.get("attendant_name"),
        location=body.get("location"),
        transaction_datetime=(
            datetime.fromisoformat(body["transaction_datetime"])
            if body.get("transaction_datetime") else datetime.utcnow()
        ),
        receipt_number=body.get("receipt_number"),
        amount=float(body["amount"]) if body.get("amount") else None,
        currency=body.get("currency"),
        custom_attributes=body.get("custom_attributes", {}),
        session_token_hash=token_hash,
        expires_at=datetime.utcnow() + timedelta(hours=24),
    )
    db.add(txn)
    await db.flush()

    # Get org slug from client or fall back
    org_slug = getattr(ctx.client, "name", "RIVIWA").upper().replace(" ", "")[:20]

    # Call qr_service to generate QR code + short code
    qr_data = await _call_qr_service(
        org_id=str(org_id),
        org_slug=org_slug,
        integration_client_id=str(ctx.client.id),
        receipt_transaction_id=str(txn.id),
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
        custom_attributes=body.get("custom_attributes", {}),
    )

    # Update transaction with QR codes
    if qr_data:
        txn.short_code = qr_data.get("short_code")
        txn.sms_code = qr_data.get("sms_code")
        txn.qr_image_url = qr_data.get("qr_image_url")
        txn.qr_receipt_id = uuid.UUID(qr_data["receipt_session_id"]) if qr_data.get("receipt_session_id") else None

    await db.commit()
    await db.refresh(txn)

    log.info("integration.receipt.created",
             client_id=str(ctx.client.id), org_id=str(org_id),
             receipt_number=body.get("receipt_number"),
             short_code=txn.short_code)

    response = {
        "transaction_id": str(txn.id),
        "receipt_number": txn.receipt_number,
        "session_token": session_token,
        "expires_at": txn.expires_at.isoformat(),
    }

    if qr_data:
        response.update({
            "unique_code": qr_data.get("sms_code"),
            "short_code": qr_data.get("short_code"),
            "qr_image_url": qr_data.get("qr_image_url"),
            "qr_redirect_url": qr_data.get("qr_redirect_url"),
        })
        # SMS instructions for feature phones
        response["sms_instructions"] = {
            "number": getattr(settings, "SMS_SHORT_NUMBER", "+255XXXXXXX"),
            "text": f"Send '{qr_data.get('sms_code', '')}' to {getattr(settings, 'SMS_SHORT_NUMBER', '+255XXXXXXX')}",
            "note": "Customers with basic phones can text this code to submit feedback",
        }
    else:
        # QR generation failed — return session token only (graceful degradation)
        log.warning("integration.receipt.qr_failed", transaction_id=str(txn.id))
        response["warning"] = "QR generation is temporarily unavailable. Session token can still be used for web redirect."

    return response


async def _call_qr_service(**kwargs) -> Optional[dict]:
    """Call qr_service internal endpoint to generate receipt QR + short code."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{settings.QR_SERVICE_URL}/api/v1/internal/qr/receipt",
                json=kwargs,
                headers={
                    "X-Service-Key": settings.INTERNAL_SERVICE_KEY,
                    "Content-Type": "application/json",
                },
            )
            if resp.status_code in (200, 201):
                return resp.json()
            log.warning("qr_service.receipt_failed", status=resp.status_code, body=resp.text[:200])
    except Exception as exc:
        log.error("qr_service.call_error", error=str(exc))
    return None

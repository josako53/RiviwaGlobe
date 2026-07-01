"""api/v1/internal.py — payment_service internal endpoints (service-to-service only)"""
from __future__ import annotations

import uuid
from typing import Annotated, Optional

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.dependencies import DbDep
from core.exceptions import PaymentNotFoundError
from services.payment_service import PaymentService

log = structlog.get_logger(__name__)


# ── Service-key auth ──────────────────────────────────────────────────────────

async def _require_service_key(
    x_service_key: Annotated[Optional[str], Header(alias="X-Service-Key")] = None,
) -> None:
    """Reject requests that do not carry a valid internal service key."""
    if not x_service_key or x_service_key != settings.INTERNAL_SERVICE_KEY:
        raise HTTPException(status_code=403, detail="Invalid or missing service key.")


# All routes in this module are secured by X-Service-Key at the router level.
router = APIRouter(
    prefix="/internal/payments",
    tags=["Internal — Payments"],
    dependencies=[Depends(_require_service_key)],
)


# ── Serialisation helpers (mirror payments.py) ────────────────────────────────

def _p(p) -> dict:
    return {
        "id":             str(p.id),
        "payment_type":   p.payment_type.value,
        "amount":         p.amount,
        "currency":       p.currency.value,
        "description":    p.description,
        "status":         p.status.value,
        "external_ref":   p.external_ref,
        "payer_user_id":  str(p.payer_user_id)  if p.payer_user_id  else None,
        "payer_phone":    p.payer_phone,
        "payer_name":     p.payer_name,
        "org_id":         str(p.org_id)         if p.org_id         else None,
        "project_id":     str(p.project_id)     if p.project_id     else None,
        "reference_id":   str(p.reference_id)   if p.reference_id   else None,
        "reference_type": p.reference_type,
        "created_at":     p.created_at.isoformat(),
        "expires_at":     p.expires_at.isoformat() if p.expires_at else None,
        "paid_at":        p.paid_at.isoformat()    if p.paid_at    else None,
    }


def _t(t) -> dict:
    return {
        "id":               str(t.id),
        "payment_id":       str(t.payment_id),
        "provider":         t.provider.value,
        "status":           t.status.value,
        "provider_ref":     t.provider_ref,
        "provider_receipt": t.provider_receipt,
        "settled_amount":   t.settled_amount,
        "failure_reason":   t.failure_reason,
        "initiated_at":     t.initiated_at.isoformat(),
        "completed_at":     t.completed_at.isoformat() if t.completed_at else None,
    }


def _svc(db: AsyncSession) -> PaymentService:
    return PaymentService(db=db)


# ── GET /api/v1/internal/payments/lookup ─────────────────────────────────────

@router.get("/lookup", summary="[Internal] Lookup payments by reference, user, phone, or amount")
async def lookup_payments(
    db:           DbDep,
    reference_id: Optional[uuid.UUID] = Query(default=None, description="Domain-object reference UUID"),
    user_id:      Optional[uuid.UUID] = Query(default=None, description="Payer user UUID"),
    phone:        Optional[str]       = Query(default=None, description="Payer phone (substring match)"),
    amount:       Optional[float]     = Query(default=None, description="Exact payment amount"),
    org_id:       Optional[uuid.UUID] = Query(default=None, description="Organisation UUID"),
    skip:         int                 = Query(default=0, ge=0),
    limit:        int                 = Query(default=50, ge=1, le=200),
) -> dict:
    """
    Lookup payments matching one or more criteria.

    Returns each matching payment with its latest transaction status attached.
    At least one filter should be provided for useful results; with no filters the
    most recent `limit` payments across the whole service are returned.

    Intended for service-to-service calls only (e.g. AI service correlating a
    payment to a feedback record, subscription service verifying a settlement).
    """
    svc      = _svc(db)
    payments = await svc.list_payments(
        payer_user_id=user_id,
        org_id=org_id,
        reference_id=reference_id,
        skip=skip,
        limit=limit,
    )

    # Phone and amount are not handled by the repo — filter in Python.
    # Volume here is bounded by `limit` so this is acceptable.
    if phone:
        payments = [p for p in payments if p.payer_phone and phone in p.payer_phone]
    if amount is not None:
        payments = [p for p in payments if p.amount == amount]

    items = []
    for p in payments:
        latest_txn = await svc.get_latest_transaction(p.id)
        entry = _p(p)
        entry["latest_transaction"] = _t(latest_txn) if latest_txn else None
        items.append(entry)

    return {"items": items, "count": len(items)}


# ── GET /api/v1/internal/payments/{payment_id}/status ────────────────────────

@router.get("/{payment_id}/status", summary="[Internal] Payment status and all transaction attempts")
async def get_payment_status(
    payment_id: uuid.UUID,
    db:         DbDep,
) -> dict:
    """
    Return the current status and every transaction attempt for a specific payment.

    Intended for service-to-service calls only.
    """
    svc = _svc(db)
    try:
        payment = await svc.get_payment(payment_id)
    except PaymentNotFoundError:
        raise HTTPException(status_code=404, detail="Payment not found.")
    txns = await svc.list_transactions(payment_id)
    return {
        **_p(payment),
        "transactions": [_t(t) for t in txns],
    }

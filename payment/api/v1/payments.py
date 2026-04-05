"""api/v1/payments.py — HTTP orchestration only"""
from __future__ import annotations
import uuid
from typing import Any, Dict, Optional
from fastapi import APIRouter, Query, status
from core.dependencies import AuthDep, DbDep, StaffDep
from events.producer import get_producer
from models.payment import Currency, PaymentProvider, PaymentStatus, PaymentType
from services.payment_service import PaymentService

router = APIRouter(prefix="/payments", tags=["Payments"])

def _svc(db, producer=None): return PaymentService(db=db, producer=producer)

def _p(p) -> dict:
    return {
        "id": str(p.id), "payment_type": p.payment_type.value,
        "amount": p.amount, "currency": p.currency.value,
        "description": p.description, "status": p.status.value,
        "external_ref": p.external_ref,
        "payer_user_id":  str(p.payer_user_id)  if p.payer_user_id  else None,
        "payer_phone": p.payer_phone, "payer_name": p.payer_name,
        "org_id":       str(p.org_id)       if p.org_id       else None,
        "project_id":   str(p.project_id)   if p.project_id   else None,
        "reference_id": str(p.reference_id) if p.reference_id else None,
        "reference_type": p.reference_type,
        "created_at": p.created_at.isoformat(),
        "expires_at": p.expires_at.isoformat() if p.expires_at else None,
        "paid_at":    p.paid_at.isoformat()    if p.paid_at    else None,
    }

def _t(t) -> dict:
    return {
        "id": str(t.id), "payment_id": str(t.payment_id),
        "provider": t.provider.value, "status": t.status.value,
        "provider_ref": t.provider_ref, "provider_receipt": t.provider_receipt,
        "settled_amount": t.settled_amount, "failure_reason": t.failure_reason,
        "initiated_at": t.initiated_at.isoformat(),
        "completed_at": t.completed_at.isoformat() if t.completed_at else None,
    }


@router.post("", status_code=status.HTTP_201_CREATED, summary="Create payment intent")
async def create_payment(body: Dict[str, Any], db: DbDep, token: AuthDep) -> dict:
    """Create payment intent. Does not contact provider — call /initiate next."""
    payment = await _svc(db).create_payment(
        payment_type   = PaymentType(body["payment_type"]),
        amount         = float(body["amount"]),
        currency       = Currency(body.get("currency", "TZS")),
        phone          = body["phone"],
        payer_user_id  = token.sub,
        payer_name     = body.get("payer_name"),
        payer_email    = body.get("payer_email"),
        description    = body.get("description"),
        org_id         = uuid.UUID(body["org_id"])       if body.get("org_id")       else None,
        project_id     = uuid.UUID(body["project_id"])   if body.get("project_id")   else None,
        reference_id   = uuid.UUID(body["reference_id"]) if body.get("reference_id") else None,
        reference_type = body.get("reference_type"),
        created_by     = token.sub,
    )
    return _p(payment)


@router.get("", summary="List payments")
async def list_payments(
    db: DbDep, token: AuthDep,
    payer_user_id: Optional[uuid.UUID] = Query(default=None),
    org_id:        Optional[uuid.UUID] = Query(default=None),
    project_id:    Optional[uuid.UUID] = Query(default=None),
    reference_id:  Optional[uuid.UUID] = Query(default=None),
    status_:       Optional[str]       = Query(default=None, alias="status"),
    payment_type:  Optional[str]       = Query(default=None),
    skip: int = Query(default=0, ge=0), limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    is_staff = token.org_role in ("owner","admin","manager") or \
               token.platform_role in ("super_admin","admin","moderator")
    effective_payer = payer_user_id if is_staff else token.sub
    items = await _svc(db).list_payments(
        payer_user_id=effective_payer, org_id=org_id, project_id=project_id,
        reference_id=reference_id, status=status_, payment_type=payment_type,
        skip=skip, limit=limit,
    )
    return {"items": [_p(i) for i in items], "count": len(items)}


@router.get("/{payment_id}", summary="Payment detail with transactions")
async def get_payment(payment_id: uuid.UUID, db: DbDep, token: AuthDep) -> dict:
    svc     = _svc(db)
    payment = await svc.get_payment(payment_id)
    txns    = await svc.list_transactions(payment_id)
    return {**_p(payment), "transactions": [_t(t) for t in txns]}


@router.post("/{payment_id}/initiate", summary="Initiate USSD push via provider")
async def initiate_payment(payment_id: uuid.UUID, body: Dict[str, Any], db: DbDep, token: AuthDep) -> dict:
    """
    Send payment request to the chosen provider.
    Required body: provider — "azampay" | "selcom" | "mpesa"

    azampay  → Airtel TZ, M-Pesa (via AzamPay), CRDB, NMB
    selcom   → Tigo Pesa, TTCL Pesa, Halotel
    mpesa    → Vodacom M-Pesa TZ (direct)
    """
    provider = PaymentProvider(body.get("provider", "azampay"))
    producer = await get_producer()
    txn      = await _svc(db, producer).initiate(payment_id, provider)
    return {
        **_t(txn),
        "checkout_url": (txn.provider_response or {}).get("checkout_url"),
        "message": "Payment request sent. Customer will receive a USSD prompt.",
    }


@router.post("/{payment_id}/verify", summary="Poll provider for latest status")
async def verify_payment(payment_id: uuid.UUID, db: DbDep, token: AuthDep) -> dict:
    svc = _svc(db)
    txn = await svc.get_latest_transaction(payment_id)
    if not txn:
        from core.exceptions import PaymentNotFoundError
        raise PaymentNotFoundError()
    return _t(await svc.verify(txn.id))


@router.post("/{payment_id}/refund", summary="Refund a paid payment [staff]")
async def refund_payment(payment_id: uuid.UUID, db: DbDep, _: StaffDep) -> dict:
    producer = await get_producer()
    txn      = await _svc(db, producer).refund(payment_id)
    return {**_t(txn), "message": "Refund initiated."}


@router.delete("/{payment_id}", summary="Cancel a PENDING payment")
async def cancel_payment(payment_id: uuid.UUID, db: DbDep, token: AuthDep) -> dict:
    payment = await _svc(db).cancel(payment_id)
    return {"message": "Payment cancelled.", "payment_id": str(payment.id)}


@router.get("/{payment_id}/transactions", summary="List transactions for a payment")
async def list_transactions(payment_id: uuid.UUID, db: DbDep, token: AuthDep) -> dict:
    items = await _svc(db).list_transactions(payment_id)
    return {"items": [_t(t) for t in items], "count": len(items)}

"""api/v1/checkout.py — Subscription checkout and payment webhook handling."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

import structlog
from fastapi import APIRouter, Request
from sqlalchemy import select

from core.deps import DbDep, OrgIdDep, TokenDep
from core.exceptions import NotFoundError, PaymentError
from models.subscription import Invoice, InvoiceStatus, PaymentMethod, Subscription, SubscriptionStatus
from services.payment_gateway import process_payment
from services.subscription_svc import SubscriptionService

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/checkout", tags=["Checkout"])


@router.post("", summary="Subscribe to a plan — checkout", status_code=201)
async def checkout(body: dict, db: DbDep, claims: TokenDep, org_id: OrgIdDep) -> dict:
    """
    Full checkout flow:
    1. Validate plan + promo
    2. Create subscription + invoice
    3. Charge payment method
    4. Activate subscription on payment success

    Body:
    {
      "plan_id": "uuid",
      "billing_cycle": "monthly" | "annual",
      "payment_method_id": "uuid",      # optional if already saved
      "payment_method": {               # or inline new method
        "type": "mpesa",
        "phone_number": "+255712345678"
      },
      "promo_code": "RIVIWA50"          # optional
    }
    """
    svc = SubscriptionService(db)

    # Resolve payment method
    pm_id = body.get("payment_method_id")
    pm_inline = body.get("payment_method")
    pm: Optional[PaymentMethod] = None

    if pm_id:
        pm = await db.get(PaymentMethod, uuid.UUID(pm_id))
        if not pm or str(pm.org_id) != org_id:
            raise NotFoundError("Payment method")
    elif pm_inline:
        pm = PaymentMethod(
            org_id=uuid.UUID(org_id),
            type=pm_inline["type"],
            phone_number=pm_inline.get("phone_number"),
            display_name=pm_inline.get("display_name", ""),
            provider_ref=pm_inline.get("provider_ref"),
            is_default=pm_inline.get("is_default", False),
        )
        db.add(pm)
        await db.flush()

    # Create subscription + invoice
    sub, invoice = await svc.create_subscription(
        org_id=org_id,
        plan_id=body["plan_id"],
        billing_cycle=body.get("billing_cycle", "monthly"),
        payment_method_id=str(pm.id) if pm else None,
        promo_code=body.get("promo_code"),
        actor_id=claims.get("sub"),
    )

    # Skip payment if trial (no charge yet)
    if sub.status == SubscriptionStatus.TRIALING.value:
        return _checkout_response(sub, invoice, payment_result=None)

    # Enterprise / bank transfer — manual payment
    if pm and pm.type == "bank_transfer":
        payment_result = {"provider": "bank_transfer", "success": True, "manual": True,
                          "instructions": f"Wire USD {invoice.total_usd} to Riviwa bank account. Reference: {invoice.invoice_number}"}
        invoice.payment_method_type = "bank_transfer"
        await db.commit()
        return _checkout_response(sub, invoice, payment_result)

    if not pm:
        # Return invoice — org can pay later
        return _checkout_response(sub, invoice, payment_result=None,
                                  message="Subscription created. Complete payment to activate.")

    # Process payment
    payment_result = await process_payment(
        method_type=pm.type,
        phone=pm.phone_number,
        stripe_pm_id=pm.provider_ref,
        amount_usd=invoice.total_usd,
        invoice_id=str(invoice.id),
        invoice_number=invoice.invoice_number,
    )

    if payment_result.get("success"):
        invoice.status = InvoiceStatus.PAID.value
        invoice.paid_at = datetime.utcnow()
        invoice.payment_method_type = pm.type
        invoice.payment_reference = payment_result.get("external_id") or payment_result.get("payment_intent_id")
        sub.status = SubscriptionStatus.ACTIVE.value
        await db.commit()
        log.info("checkout.payment_success", org_id=org_id, invoice=invoice.invoice_number)
    else:
        invoice.status = InvoiceStatus.OPEN.value
        await db.commit()
        log.warning("checkout.payment_failed", org_id=org_id, invoice=invoice.invoice_number)
        raise PaymentError(f"Payment failed: {payment_result.get('raw', {}).get('message', 'Unknown error')}. "
                           "Please try again or use a different payment method.")

    return _checkout_response(sub, invoice, payment_result)


@router.post("/pay-invoice/{invoice_id}", summary="Pay an outstanding invoice")
async def pay_invoice(invoice_id: str, body: dict, db: DbDep, org_id: OrgIdDep) -> dict:
    inv = await db.get(Invoice, uuid.UUID(invoice_id))
    if not inv or str(inv.org_id) != org_id:
        raise NotFoundError("Invoice")
    if inv.status == InvoiceStatus.PAID.value:
        return {"message": "Invoice is already paid.", "invoice_number": inv.invoice_number}

    pm_id = body.get("payment_method_id")
    pm = await db.get(PaymentMethod, uuid.UUID(pm_id)) if pm_id else None

    payment_result = await process_payment(
        method_type=pm.type if pm else body.get("type", "bank_transfer"),
        phone=pm.phone_number if pm else body.get("phone_number"),
        stripe_pm_id=pm.provider_ref if pm else None,
        amount_usd=inv.total_usd,
        invoice_id=str(inv.id),
        invoice_number=inv.invoice_number,
    )

    if payment_result.get("success"):
        inv.status = InvoiceStatus.PAID.value
        inv.paid_at = datetime.utcnow()
        inv.payment_method_type = pm.type if pm else "manual"
        inv.payment_reference = payment_result.get("external_id") or payment_result.get("payment_intent_id")
        # Reactivate if past_due
        sub = await db.get(Subscription, inv.subscription_id)
        if sub and sub.status == SubscriptionStatus.PAST_DUE.value:
            sub.status = SubscriptionStatus.ACTIVE.value
        await db.commit()
        return {"message": "Payment successful.", "invoice_number": inv.invoice_number}

    raise PaymentError("Payment failed. Please try again.")


# ── Webhooks (provider callbacks) ─────────────────────────────────────────────

@router.post("/success", include_in_schema=False)
async def checkout_success(request: Request) -> dict:
    return {"status": "ok"}


@router.post("/cancel", include_in_schema=False)
async def checkout_cancel(request: Request) -> dict:
    return {"status": "cancelled"}


@router.post("/webhooks/azampay", include_in_schema=False)
async def webhook_azampay(request: Request, db: DbDep) -> dict:
    data = await request.json()
    log.info("webhook.azampay", data=data)
    await _handle_payment_callback(db, reference=data.get("externalId"), success=data.get("success"))
    return {"status": "ok"}


@router.post("/webhooks/selcom", include_in_schema=False)
async def webhook_selcom(request: Request, db: DbDep) -> dict:
    data = await request.json()
    log.info("webhook.selcom", data=data)
    await _handle_payment_callback(db, reference=data.get("order_id"), success=data.get("resultcode") == "000")
    return {"status": "ok"}


@router.post("/webhooks/mpesa", include_in_schema=False)
async def webhook_mpesa(request: Request, db: DbDep) -> dict:
    data = await request.json()
    log.info("webhook.mpesa", data=data)
    await _handle_payment_callback(db, reference=data.get("input_ThirdPartyConversationID"),
                                   success=data.get("output_ResponseCode") == "INS-0")
    return {"status": "ok"}


async def _handle_payment_callback(db, reference: Optional[str], success: bool) -> None:
    if not reference:
        return
    # Find invoice by payment_reference or invoice_id
    inv = (await db.execute(
        select(Invoice).where(Invoice.payment_reference == reference)
    )).scalar_one_or_none()
    if not inv:
        return
    if success and inv.status != InvoiceStatus.PAID.value:
        inv.status = InvoiceStatus.PAID.value
        inv.paid_at = datetime.utcnow()
        sub = await db.get(Subscription, inv.subscription_id)
        if sub and sub.status in (SubscriptionStatus.PAST_DUE.value, SubscriptionStatus.TRIALING.value):
            sub.status = SubscriptionStatus.ACTIVE.value
        await db.commit()


def _checkout_response(sub: Subscription, invoice: Invoice, payment_result, message: str = "") -> dict:
    return {
        "subscription_id": str(sub.id),
        "status": sub.status,
        "invoice": {
            "invoice_number": invoice.invoice_number,
            "total_usd": str(invoice.total_usd),
            "status": invoice.status,
            "due_date": invoice.due_date.isoformat(),
        },
        "payment": payment_result,
        "message": message or ("Subscription active." if invoice.status == InvoiceStatus.PAID.value
                               else "Invoice created. Complete payment to activate."),
        "next_renewal": sub.current_period_end.isoformat(),
    }

"""api/v1/checkout.py — Subscription checkout via payment_service."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

import structlog
from fastapi import APIRouter, Request
from sqlalchemy import select

from core.deps import DbDep, OrgIdDep, TokenDep
from core.exceptions import NotFoundError, PaymentError, ValidationError
from models.subscription import Invoice, InvoiceStatus, PaymentMethod, Plan, Subscription, SubscriptionStatus
from services.payment_client import create_payment, get_payment_status, initiate_payment
from services.subscription_svc import SubscriptionService
from services.auth_client import notify_payment_verified

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/checkout", tags=["Checkout"])

SUPPORTED_PROVIDERS = {"mpesa", "azampay", "selcom", "paypal", "airtel", "yas", "bank_transfer"}


@router.post("", summary="Subscribe to a plan — checkout", status_code=201)
async def checkout(body: dict, db: DbDep, claims: TokenDep, org_id: OrgIdDep) -> dict:
    """
    Full checkout flow — delegates payment to payment_service.

    Request body:
    {
      "plan_id":        "uuid",
      "billing_cycle":  "monthly" | "annual",
      "provider":       "mpesa" | "azampay" | "selcom" | "paypal" | "bank_transfer",
      "phone_number":   "+255712345678",   # required for mobile money
      "payer_name":     "John Komba",
      "payer_email":    "john@example.com",
      "promo_code":     "RIVIWA50",        # optional
      "save_method":    true               # save payment method for future use
    }
    """
    plan_id = body.get("plan_id")
    if not plan_id:
        raise ValidationError("plan_id is required.")

    svc      = SubscriptionService(db)
    provider = body.get("provider", "bank_transfer").lower()

    if provider not in SUPPORTED_PROVIDERS:
        raise PaymentError(f"Unsupported provider '{provider}'. Use: {', '.join(SUPPORTED_PROVIDERS)}")

    # Auto-apply best active sale if no promo code provided
    promo_code = body.get("promo_code")
    active_sale = None
    if not promo_code:
        from api.v1.sales import get_best_auto_apply_sale
        plan = await db.get(Plan, uuid.UUID(plan_id))
        if plan:
            existing_sub = await svc.get_org_subscription(org_id)
            is_new = existing_sub is None
            active_sale = await get_best_auto_apply_sale(
                db, plan.slug, body.get("billing_cycle", "monthly"), is_new
            )
            if active_sale:
                log.info("checkout.auto_sale_applied", sale=active_sale.name, org_id=org_id)

    # Create subscription + invoice
    sub, invoice = await svc.create_subscription(
        org_id=org_id,
        plan_id=plan_id,
        billing_cycle=body.get("billing_cycle", "monthly"),
        promo_code=promo_code,
        actor_id=claims.get("sub"),
    )

    # If sale was auto-applied, increment redemption count
    if active_sale:
        from models.subscription import Sale
        sale_obj = await db.get(Sale, active_sale.id)
        if sale_obj:
            sale_obj.redemption_count += 1
            await db.flush()

    # Save payment method if requested
    if body.get("save_method") and body.get("phone_number"):
        pm = PaymentMethod(
            org_id=uuid.UUID(org_id),
            type=provider,
            phone_number=body.get("phone_number"),
            display_name=body.get("payer_name", ""),
            is_default=True,
        )
        db.add(pm)
        sub.default_payment_method_id = pm.id
        await db.flush()

    # Bank transfer — no gateway call, return invoice for manual payment
    if provider == "bank_transfer":
        await db.commit()
        # Payment verification happens when bank transfer is confirmed (see payment_confirmed_callback)
        return {
            "subscription_id": str(sub.id),
            "status": sub.status,
            "invoice": _invoice_out(invoice),
            "payment": {
                "provider": "bank_transfer",
                "instructions": (
                    f"Transfer USD {invoice.total_usd} to Riviwa. "
                    f"Reference: {invoice.invoice_number}. "
                    "Send proof to billing@riviwa.com."
                ),
            },
            "message": "Invoice created. Complete bank transfer to activate.",
        }

    # Create payment intent in payment_service
    try:
        payment = await create_payment(
            org_id=org_id,
            amount_usd=invoice.total_usd,
            invoice_id=str(invoice.id),
            invoice_number=invoice.invoice_number,
            payer_phone=body.get("phone_number"),
            payer_email=body.get("payer_email"),
            payer_name=body.get("payer_name"),
            internal_token=claims.get("_raw_token"),
        )
        payment_id = payment["id"]

        # Store payment_service payment_id in invoice
        invoice.payment_reference = payment_id
        invoice.payment_method_type = provider
        await db.commit()

        # Initiate with the provider (returns checkout_url for PayPal/Selcom)
        txn = await initiate_payment(payment_id=payment_id, provider=provider,
                                     internal_token=claims.get("_raw_token"))

        checkout_url = txn.get("checkout_url")
        log.info("checkout.initiated", org_id=org_id, provider=provider,
                 invoice=invoice.invoice_number, has_redirect=bool(checkout_url))

        return {
            "subscription_id":  str(sub.id),
            "status":           sub.status,
            "payment_id":       payment_id,
            "invoice":          _invoice_out(invoice),
            "checkout_url":     checkout_url,
            "payment": {
                "provider":      provider,
                "status":        "pending",
                "transaction_id": txn.get("id"),
                "message":       _provider_message(provider, checkout_url),
            },
            "message": (
                "Redirecting to PayPal for payment." if checkout_url
                else "USSD prompt sent to your phone. Enter your PIN to complete payment."
            ),
            "next_renewal": sub.current_period_end.isoformat(),
        }

    except Exception as exc:
        log.error("checkout.payment_failed", org_id=org_id, provider=provider, error=str(exc))
        raise PaymentError(f"Payment initiation failed: {str(exc)[:200]}")


@router.get("/status/{payment_id}", summary="Check payment status (poll)")
async def payment_status(payment_id: str, db: DbDep, claims: TokenDep, org_id: OrgIdDep) -> dict:
    """Poll payment_service for payment status. Activate subscription on success."""
    try:
        payment = await get_payment_status(payment_id, internal_token=claims.get("_raw_token"))
    except Exception as exc:
        raise NotFoundError("Payment")

    paid = payment.get("status") == "paid"
    if paid:
        # Find invoice and activate subscription
        inv = (await db.execute(
            select(Invoice).where(Invoice.payment_reference == payment_id)
        )).scalar_one_or_none()
        if inv and inv.status != InvoiceStatus.PAID.value:
            inv.status = InvoiceStatus.PAID.value
            inv.paid_at = datetime.utcnow()
            sub = await db.get(Subscription, inv.subscription_id)
            if sub and sub.status in (SubscriptionStatus.TRIALING.value, SubscriptionStatus.PAST_DUE.value):
                sub.status = SubscriptionStatus.ACTIVE.value
            await db.commit()
            # Auto-verify org on payment confirmation
            notify_payment_verified(org_id)

    return {
        "payment_id":   payment_id,
        "payment_status": payment.get("status"),
        "paid":         paid,
        "subscription_active": paid,
    }


# ── Payment method management ─────────────────────────────────────────────────

@router.post("/pay-invoice/{invoice_id}", summary="Pay an outstanding invoice")
async def pay_invoice(invoice_id: str, body: dict, db: DbDep, claims: TokenDep, org_id: OrgIdDep) -> dict:
    inv = await db.get(Invoice, uuid.UUID(invoice_id))
    if not inv or str(inv.org_id) != org_id:
        raise NotFoundError("Invoice")
    if inv.status == InvoiceStatus.PAID.value:
        return {"message": "Invoice already paid.", "invoice_number": inv.invoice_number}

    provider = body.get("provider", "bank_transfer")
    try:
        payment = await create_payment(
            org_id=org_id, amount_usd=inv.total_usd,
            invoice_id=str(inv.id), invoice_number=inv.invoice_number,
            payer_phone=body.get("phone_number"),
            internal_token=claims.get("_raw_token"),
        )
        txn = await initiate_payment(payment["id"], provider,
                                     internal_token=claims.get("_raw_token"))
        inv.payment_reference = payment["id"]
        inv.payment_method_type = provider
        await db.commit()
        return {
            "invoice_number": inv.invoice_number,
            "payment_id": payment["id"],
            "checkout_url": txn.get("checkout_url"),
            "message": _provider_message(provider, txn.get("checkout_url")),
        }
    except Exception as exc:
        raise PaymentError(str(exc)[:200])


# ── Webhook receiver (from payment_service Kafka or direct callback) ──────────

@router.post("/webhooks/payment-confirmed", include_in_schema=False)
async def payment_confirmed_callback(request: Request, db: DbDep) -> dict:
    """Called by Kafka consumer when payment_service confirms a payment."""
    data = await request.json()
    reference_id = data.get("reference_id")
    if reference_id:
        inv = await db.get(Invoice, uuid.UUID(reference_id))
        if inv and inv.status != InvoiceStatus.PAID.value:
            inv.status = InvoiceStatus.PAID.value
            inv.paid_at = datetime.utcnow()
            sub = await db.get(Subscription, inv.subscription_id)
            if sub:
                sub.status = SubscriptionStatus.ACTIVE.value
                notify_payment_verified(str(sub.org_id))
            await db.commit()
    return {"status": "ok"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _invoice_out(inv: Invoice) -> dict:
    return {
        "invoice_number": inv.invoice_number,
        "total_usd":      str(inv.total_usd),
        "status":         inv.status,
        "due_date":       inv.due_date.isoformat(),
        "line_items":     inv.line_items,
    }


def _provider_message(provider: str, checkout_url: Optional[str]) -> str:
    if provider == "paypal" and checkout_url:
        return f"Redirect user to: {checkout_url}"
    if provider == "selcom" and checkout_url:
        return f"Open payment page: {checkout_url}"
    if provider in ("mpesa", "azampay"):
        return "USSD prompt sent. Customer enters PIN on their phone."
    return "Payment initiated."

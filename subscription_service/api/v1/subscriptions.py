"""api/v1/subscriptions.py — Org subscription lifecycle management."""
from __future__ import annotations

import uuid
from typing import Optional
from fastapi import APIRouter, Query
from sqlalchemy import select, desc

from core.deps import DbDep, TokenDep, OrgIdDep, AdminDep, ServiceKeyDep
from core.exceptions import NotFoundError
from models.subscription import (
    Invoice, InvoiceStatus, OrgAddOn, PaymentMethod,
    PromoCode, Subscription, SubscriptionEvent, SubscriptionStatus, UsageMeter, Plan
)
from services.subscription_svc import SubscriptionService

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


def _sub_out(sub: Subscription, plan: Optional[Plan] = None) -> dict:
    return {
        "id": str(sub.id),
        "org_id": str(sub.org_id),
        "plan_id": str(sub.plan_id),
        "plan": {"slug": plan.slug, "display_name": plan.display_name} if plan else None,
        "status": sub.status,
        "billing_cycle": sub.billing_cycle,
        "current_period_start": sub.current_period_start.isoformat(),
        "current_period_end": sub.current_period_end.isoformat(),
        "trial_end": sub.trial_end.isoformat() if sub.trial_end else None,
        "cancel_at_period_end": sub.cancel_at_period_end,
        "cancelled_at": sub.cancelled_at.isoformat() if sub.cancelled_at else None,
        "paused_at": sub.paused_at.isoformat() if sub.paused_at else None,
        "pause_resume_at": sub.pause_resume_at.isoformat() if sub.pause_resume_at else None,
        "discount_pct": str(sub.discount_pct),
        "discount_months_remaining": sub.discount_months_remaining,
        "effective_monthly_usd": str(sub.effective_monthly_usd),
        "created_at": sub.created_at.isoformat(),
    }


def _invoice_out(inv: Invoice) -> dict:
    return {
        "id": str(inv.id),
        "invoice_number": inv.invoice_number,
        "status": inv.status,
        "subtotal_usd": str(inv.subtotal_usd),
        "discount_usd": str(inv.discount_usd),
        "tax_usd": str(inv.tax_usd),
        "total_usd": str(inv.total_usd),
        "billing_period_start": inv.billing_period_start.isoformat(),
        "billing_period_end": inv.billing_period_end.isoformat(),
        "due_date": inv.due_date.isoformat(),
        "paid_at": inv.paid_at.isoformat() if inv.paid_at else None,
        "payment_method_type": inv.payment_method_type,
        "payment_reference": inv.payment_reference,
        "line_items": inv.line_items,
        "pdf_url": inv.pdf_url,
        "created_at": inv.created_at.isoformat(),
    }


# ── Current subscription ──────────────────────────────────────────────────────

@router.get("/current", summary="Get organisation's current subscription")
async def get_current(db: DbDep, org_id: OrgIdDep) -> dict:
    svc = SubscriptionService(db)
    sub = await svc.get_org_subscription(org_id)
    if not sub:
        return {"subscription": None, "has_subscription": False}
    plan = await db.get(Plan, sub.plan_id)
    usage = await svc.get_usage(org_id)
    limits = await svc.get_limits(org_id)

    usage_out = {}
    if usage:
        usage_out = {
            "submissions":   {"used": usage.submissions_count,   "limit": limits.get("max_submissions_per_month", 0)},
            "sms":           {"used": usage.sms_count,           "limit": limits.get("max_sms_per_month", 0)},
            "api_calls":     {"used": usage.api_calls_count,     "limit": limits.get("max_api_calls_per_month", 0)},
            "storage_bytes": {"used": usage.storage_bytes,       "limit": limits.get("max_storage_gb", 0) * 1_073_741_824},
            "qr_codes":      {"used": usage.qr_codes_count,      "limit": limits.get("max_qr_per_month", 0)},
            "team_members":  {"used": usage.team_members_count,  "limit": limits.get("max_team_members", 0)},
        }

    return {
        "has_subscription": True,
        "subscription": _sub_out(sub, plan),
        "usage": usage_out,
    }


# ── Upgrade ───────────────────────────────────────────────────────────────────

@router.post("/upgrade", summary="Upgrade to a higher plan")
async def upgrade(body: dict, db: DbDep, claims: TokenDep, org_id: OrgIdDep) -> dict:
    svc = SubscriptionService(db)
    sub = await svc.upgrade(org_id, body["plan_id"], actor_id=claims.get("sub"))
    plan = await db.get(Plan, sub.plan_id)
    return {"subscription": _sub_out(sub, plan), "message": f"Upgraded to {plan.display_name} successfully."}


# ── Downgrade ─────────────────────────────────────────────────────────────────

@router.post("/downgrade", summary="Downgrade to a lower plan")
async def downgrade(body: dict, db: DbDep, claims: TokenDep, org_id: OrgIdDep) -> dict:
    svc = SubscriptionService(db)
    sub = await svc.downgrade(org_id, body["plan_id"], actor_id=claims.get("sub"))
    plan = await db.get(Plan, sub.plan_id)
    return {
        "subscription": _sub_out(sub, plan),
        "message": f"Downgrade to {plan.display_name} scheduled. Takes effect at period end.",
        "effective_at": sub.current_period_end.isoformat(),
    }


# ── Cancel ────────────────────────────────────────────────────────────────────

@router.post("/cancel", summary="Cancel subscription")
async def cancel(body: dict, db: DbDep, claims: TokenDep, org_id: OrgIdDep) -> dict:
    svc = SubscriptionService(db)
    sub = await svc.cancel(
        org_id,
        reason=body.get("reason"),
        immediate=body.get("immediate", False),
        actor_id=claims.get("sub"),
    )
    msg = ("Subscription cancelled immediately." if body.get("immediate")
           else f"Subscription will cancel at {sub.current_period_end.isoformat()}.")
    return {"subscription": _sub_out(sub), "message": msg}


# ── Pause ─────────────────────────────────────────────────────────────────────

@router.post("/pause", summary="Pause subscription (Business/Enterprise only)")
async def pause(body: dict, db: DbDep, claims: TokenDep, org_id: OrgIdDep) -> dict:
    svc = SubscriptionService(db)
    months = min(max(body.get("months", 1), 1), 3)
    sub = await svc.pause(org_id, months=months, actor_id=claims.get("sub"))
    return {
        "subscription": _sub_out(sub),
        "message": f"Subscription paused for {months} month(s). Resumes {sub.pause_resume_at.isoformat()}.",
    }


# ── Resume ────────────────────────────────────────────────────────────────────

@router.post("/resume", summary="Resume a paused subscription")
async def resume(db: DbDep, claims: TokenDep, org_id: OrgIdDep) -> dict:
    svc = SubscriptionService(db)
    sub = await svc.resume(org_id, actor_id=claims.get("sub"))
    plan = await db.get(Plan, sub.plan_id)
    return {"subscription": _sub_out(sub, plan), "message": "Subscription resumed successfully."}


# ── Apply promo ───────────────────────────────────────────────────────────────

@router.post("/apply-promo", summary="Apply a promo code to existing subscription")
async def apply_promo(body: dict, db: DbDep, org_id: OrgIdDep) -> dict:
    from core.exceptions import PromoError
    svc = SubscriptionService(db)
    sub = await svc.get_org_subscription(org_id)
    if not sub:
        raise PromoError("No active subscription found.")
    plan = await db.get(Plan, sub.plan_id)
    promo, discount_pct, discount_months = await svc._validate_promo(
        body["code"], plan, org_id, new_subscriber=False
    )
    from models.subscription import PromoRedemption
    import uuid as _uuid
    sub.promo_code_id = promo.id
    sub.discount_pct = discount_pct
    sub.discount_months_remaining = discount_months
    db.add(PromoRedemption(promo_code_id=promo.id, org_id=_uuid.UUID(org_id), subscription_id=sub.id))
    promo.redemption_count += 1
    await db.commit()
    return {
        "message": f"Promo code '{promo.code}' applied — {discount_pct}% off for {discount_months} month(s).",
        "discount_pct": str(discount_pct),
        "discount_months": discount_months,
    }


# ── Invoices ──────────────────────────────────────────────────────────────────

@router.get("/invoices", summary="List organisation invoices")
async def list_invoices(
    db: DbDep, org_id: OrgIdDep,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> dict:
    from sqlalchemy import func
    q = select(Invoice).where(Invoice.org_id == uuid.UUID(org_id))
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    invoices = (await db.execute(
        q.order_by(desc(Invoice.created_at)).offset((page - 1) * size).limit(size)
    )).scalars().all()
    return {"total": total, "page": page, "size": size, "invoices": [_invoice_out(i) for i in invoices]}


@router.get("/invoices/{invoice_id}", summary="Get invoice detail")
async def get_invoice(invoice_id: str, db: DbDep, org_id: OrgIdDep) -> dict:
    inv = await db.get(Invoice, uuid.UUID(invoice_id))
    if not inv or str(inv.org_id) != org_id:
        raise NotFoundError("Invoice")
    return _invoice_out(inv)


# ── Payment methods ───────────────────────────────────────────────────────────

@router.get("/payment-methods", summary="List saved payment methods")
async def list_payment_methods(db: DbDep, org_id: OrgIdDep) -> dict:
    result = await db.execute(
        select(PaymentMethod).where(
            PaymentMethod.org_id == uuid.UUID(org_id),
            PaymentMethod.is_active == True,
        ).order_by(desc(PaymentMethod.created_at))
    )
    methods = list(result.scalars().all())
    return {"payment_methods": [
        {
            "id": str(m.id), "type": m.type, "is_default": m.is_default,
            "display_name": m.display_name, "phone_number": m.phone_number,
            "card_last4": m.card_last4, "card_brand": m.card_brand,
            "card_exp_month": m.card_exp_month, "card_exp_year": m.card_exp_year,
        }
        for m in methods
    ]}


@router.post("/payment-methods", summary="Add a payment method", status_code=201)
async def add_payment_method(body: dict, db: DbDep, org_id: OrgIdDep) -> dict:
    method = PaymentMethod(
        org_id=uuid.UUID(org_id),
        type=body["type"],
        display_name=body.get("display_name", ""),
        phone_number=body.get("phone_number"),
        card_last4=body.get("card_last4"),
        card_brand=body.get("card_brand"),
        card_exp_month=body.get("card_exp_month"),
        card_exp_year=body.get("card_exp_year"),
        provider_ref=body.get("provider_ref"),
        is_default=body.get("is_default", False),
    )
    if method.is_default:
        # Unset existing defaults
        existing = (await db.execute(
            select(PaymentMethod).where(PaymentMethod.org_id == uuid.UUID(org_id), PaymentMethod.is_default == True)
        )).scalars().all()
        for m in existing:
            m.is_default = False
    db.add(method)
    await db.commit()
    await db.refresh(method)
    return {"id": str(method.id), "type": method.type, "display_name": method.display_name}


@router.delete("/payment-methods/{method_id}", summary="Remove a payment method")
async def remove_payment_method(method_id: str, db: DbDep, org_id: OrgIdDep) -> dict:
    method = await db.get(PaymentMethod, uuid.UUID(method_id))
    if not method or str(method.org_id) != org_id:
        raise NotFoundError("Payment method")
    method.is_active = False
    await db.commit()
    return {"message": "Payment method removed."}


# ── Subscription history ──────────────────────────────────────────────────────

@router.get("/events", summary="Subscription audit history")
async def list_events(db: DbDep, org_id: OrgIdDep) -> dict:
    result = await db.execute(
        select(SubscriptionEvent).where(SubscriptionEvent.org_id == uuid.UUID(org_id))
        .order_by(desc(SubscriptionEvent.created_at)).limit(50)
    )
    events = list(result.scalars().all())
    return {"events": [
        {
            "event_type": e.event_type,
            "from_plan_id": str(e.from_plan_id) if e.from_plan_id else None,
            "to_plan_id": str(e.to_plan_id) if e.to_plan_id else None,
            "metadata": e.metadata,
            "created_at": e.created_at.isoformat(),
        }
        for e in events
    ]}


# ── Feature check (internal) ──────────────────────────────────────────────────

@router.get("/internal/feature-check", summary="Internal: check feature access for an org")
async def feature_check(
    org_id: str, feature: str,
    db: DbDep, _: ServiceKeyDep,
) -> dict:
    svc = SubscriptionService(db)
    has_access = await svc.check_feature(org_id, feature)
    limits = await svc.get_limits(org_id) if has_access else {}
    return {"org_id": org_id, "feature": feature, "has_access": has_access, "limits": limits}


# ── Admin ─────────────────────────────────────────────────────────────────────

@router.get("/admin/all", summary="Admin: list all subscriptions")
async def admin_list_subscriptions(
    db: DbDep, _: AdminDep,
    status: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=50, ge=1, le=100),
) -> dict:
    from sqlalchemy import func
    q = select(Subscription)
    if status:
        q = q.where(Subscription.status == status)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    subs = (await db.execute(q.order_by(desc(Subscription.created_at)).offset((page - 1) * size).limit(size))).scalars().all()
    return {"total": total, "page": page, "size": size,
            "subscriptions": [_sub_out(s) for s in subs]}


@router.patch("/admin/{subscription_id}", summary="Admin: override subscription")
async def admin_update_subscription(
    subscription_id: str, body: dict, db: DbDep, _: AdminDep
) -> dict:
    sub = await db.get(Subscription, uuid.UUID(subscription_id))
    if not sub:
        raise NotFoundError("Subscription")
    allowed = {"status", "plan_id", "billing_cycle", "cancel_at_period_end",
               "discount_pct", "discount_months_remaining", "current_period_end"}
    from datetime import datetime
    for k, v in body.items():
        if k in allowed:
            setattr(sub, k, v)
    sub.updated_at = datetime.utcnow()
    await db.commit()
    return _sub_out(sub)

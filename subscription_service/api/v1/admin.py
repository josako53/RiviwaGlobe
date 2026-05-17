"""api/v1/admin.py — Platform owner (Riviwa admin) management endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Query
from sqlalchemy import desc, func, select

from core.deps import AdminDep, DbDep
from core.exceptions import NotFoundError
from models.subscription import (
    DunningAttempt, Invoice, InvoiceStatus, Plan, PromoCode,
    Subscription, SubscriptionEvent, SubscriptionStatus, UsageMeter,
)

router = APIRouter(prefix="/billing", tags=["Admin — Subscription Management"])


# ── Dashboard metrics ─────────────────────────────────────────────────────────

@router.get("/metrics", summary="Platform-wide subscription metrics (MRR, churn, etc.)")
async def metrics(db: DbDep, _: AdminDep) -> dict:
    # Active subscriptions by plan
    plan_counts = (await db.execute(
        select(Plan.slug, Plan.display_name, func.count(Subscription.id).label("count"),
               Plan.monthly_price_usd)
        .join(Plan, Plan.id == Subscription.plan_id)
        .where(Subscription.status == SubscriptionStatus.ACTIVE.value)
        .group_by(Plan.slug, Plan.display_name, Plan.monthly_price_usd)
    )).all()

    mrr = sum(Decimal(str(row.monthly_price_usd)) * row.count for row in plan_counts)

    # Churn (cancelled in last 30 days)
    from datetime import timedelta
    thirty_ago = datetime.utcnow() - timedelta(days=30)
    cancelled_count = (await db.execute(
        select(func.count(Subscription.id)).where(
            Subscription.status == SubscriptionStatus.CANCELLED.value,
            Subscription.cancelled_at >= thirty_ago,
        )
    )).scalar_one()

    # Total orgs with any subscription
    total_subs = (await db.execute(
        select(func.count(Subscription.id)).where(
            Subscription.status.in_([SubscriptionStatus.ACTIVE.value, SubscriptionStatus.TRIALING.value])
        )
    )).scalar_one()

    # Revenue (paid invoices this month)
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_revenue = (await db.execute(
        select(func.sum(Invoice.total_usd)).where(
            Invoice.status == InvoiceStatus.PAID.value,
            Invoice.paid_at >= month_start,
        )
    )).scalar_one() or Decimal("0")

    # Past-due count
    past_due_count = (await db.execute(
        select(func.count(Subscription.id)).where(Subscription.status == SubscriptionStatus.PAST_DUE.value)
    )).scalar_one()

    return {
        "mrr_usd": str(mrr),
        "arr_usd": str(mrr * 12),
        "monthly_revenue_usd": str(monthly_revenue),
        "active_subscriptions": total_subs,
        "churn_last_30_days": cancelled_count,
        "past_due_count": past_due_count,
        "by_plan": [
            {"slug": r.slug, "display_name": r.display_name,
             "count": r.count, "mrr_usd": str(Decimal(str(r.monthly_price_usd)) * r.count)}
            for r in plan_counts
        ],
    }


# ── Promo codes ───────────────────────────────────────────────────────────────

@router.get("/promo-codes", summary="List promo codes")
async def list_promos(
    db: DbDep, _: AdminDep,
    active_only: bool = Query(default=False),
) -> dict:
    q = select(PromoCode)
    if active_only:
        q = q.where(PromoCode.is_active == True)
    promos = (await db.execute(q.order_by(desc(PromoCode.created_at)))).scalars().all()
    return {"promo_codes": [_promo_out(p) for p in promos]}


@router.post("/promo-codes", summary="Create a promo code", status_code=201)
async def create_promo(body: dict, db: DbDep, claims: AdminDep) -> dict:
    promo = PromoCode(
        code=body["code"].upper().strip(),
        name=body["name"],
        description=body.get("description", ""),
        discount_type=body["discount_type"],
        discount_value=Decimal(str(body["discount_value"])),
        duration=body.get("duration", "once"),
        duration_months=body.get("duration_months", 1),
        max_redemptions=body.get("max_redemptions", -1),
        eligible_plans=body.get("eligible_plans"),
        new_subscribers_only=body.get("new_subscribers_only", True),
        min_plan_price_usd=Decimal(str(body.get("min_plan_price_usd", 0))),
        expires_at=datetime.fromisoformat(body["expires_at"]) if body.get("expires_at") else None,
        is_active=True,
        created_by=uuid.UUID(claims.get("sub")) if claims.get("sub") else None,
    )
    db.add(promo)
    await db.commit()
    await db.refresh(promo)
    return _promo_out(promo)


@router.patch("/promo-codes/{promo_id}", summary="Update promo code")
async def update_promo(promo_id: str, body: dict, db: DbDep, _: AdminDep) -> dict:
    promo = await db.get(PromoCode, uuid.UUID(promo_id))
    if not promo:
        raise NotFoundError("Promo code")
    for k, v in body.items():
        if hasattr(promo, k) and k not in ("id", "code", "created_at"):
            setattr(promo, k, v)
    await db.commit()
    await db.refresh(promo)
    return _promo_out(promo)


# ── Subscription overrides ────────────────────────────────────────────────────

@router.post("/subscriptions/{subscription_id}/free-months", summary="Grant free months to org")
async def grant_free_months(subscription_id: str, body: dict, db: DbDep, _: AdminDep) -> dict:
    sub = await db.get(Subscription, uuid.UUID(subscription_id))
    if not sub:
        raise NotFoundError("Subscription")
    from datetime import timedelta
    months = body.get("months", 1)
    sub.current_period_end += timedelta(days=30 * months)
    db.add(SubscriptionEvent(
        org_id=sub.org_id, subscription_id=sub.id,
        event_type="free_months_granted", actor_type="admin",
        event_meta={"months": months},
    ))
    await db.commit()
    return {"message": f"{months} free month(s) granted.", "new_period_end": sub.current_period_end.isoformat()}


@router.post("/subscriptions/{subscription_id}/cancel", summary="Admin: cancel subscription on behalf of org")
async def admin_cancel(subscription_id: str, body: dict, db: DbDep, _: AdminDep) -> dict:
    sub = await db.get(Subscription, uuid.UUID(subscription_id))
    if not sub:
        raise NotFoundError("Subscription")
    if sub.status in (SubscriptionStatus.CANCELLED.value, SubscriptionStatus.EXPIRED.value):
        return {"message": "Subscription already cancelled.", "status": sub.status}
    now = datetime.utcnow()
    if body.get("immediate", True):
        sub.status       = SubscriptionStatus.CANCELLED.value
        sub.cancelled_at = now
    else:
        sub.cancel_at_period_end = True
    sub.cancellation_reason = body.get("reason")
    sub.updated_at = now
    db.add(SubscriptionEvent(
        org_id=sub.org_id, subscription_id=sub.id,
        event_type="cancelled", actor_type="admin",
        event_meta={"reason": body.get("reason"), "immediate": body.get("immediate", True)},
    ))
    await db.commit()
    return {"message": "Subscription cancelled.", "status": sub.status}


@router.get("/subscriptions/{subscription_id}/events", summary="Subscription audit trail")
async def sub_events(subscription_id: str, db: DbDep, _: AdminDep) -> dict:
    events = (await db.execute(
        select(SubscriptionEvent).where(SubscriptionEvent.subscription_id == uuid.UUID(subscription_id))
        .order_by(desc(SubscriptionEvent.created_at))
    )).scalars().all()
    return {"events": [
        {"event_type": e.event_type, "actor_type": e.actor_type,
         "metadata": e.event_meta, "created_at": e.created_at.isoformat()}
        for e in events
    ]}


# ── Invoice management ────────────────────────────────────────────────────────

@router.get("/invoices", summary="Admin: list all invoices")
async def admin_invoices(
    db: DbDep, _: AdminDep,
    status: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=50),
) -> dict:
    q = select(Invoice)
    if status:
        q = q.where(Invoice.status == status)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    invoices = (await db.execute(q.order_by(desc(Invoice.created_at)).offset((page - 1) * size).limit(size))).scalars().all()
    return {"total": total, "page": page,
            "invoices": [{"id": str(i.id), "invoice_number": i.invoice_number,
                          "org_id": str(i.org_id), "total_usd": str(i.total_usd),
                          "status": i.status, "paid_at": i.paid_at.isoformat() if i.paid_at else None,
                          "created_at": i.created_at.isoformat()} for i in invoices]}


@router.post("/invoices/{invoice_id}/void", summary="Admin: void an invoice")
async def void_invoice(invoice_id: str, db: DbDep, _: AdminDep) -> dict:
    inv = await db.get(Invoice, uuid.UUID(invoice_id))
    if not inv:
        raise NotFoundError("Invoice")
    inv.status = InvoiceStatus.VOID.value
    inv.updated_at = datetime.utcnow()
    await db.commit()
    return {"message": "Invoice voided.", "invoice_number": inv.invoice_number}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _promo_out(p: PromoCode) -> dict:
    return {
        "id": str(p.id), "code": p.code, "name": p.name,
        "description": p.description,
        "discount_type": p.discount_type, "discount_value": str(p.discount_value),
        "duration": p.duration, "duration_months": p.duration_months,
        "max_redemptions": p.max_redemptions, "redemption_count": p.redemption_count,
        "eligible_plans": p.eligible_plans,
        "new_subscribers_only": p.new_subscribers_only,
        "expires_at": p.expires_at.isoformat() if p.expires_at else None,
        "is_active": p.is_active,
        "created_at": p.created_at.isoformat(),
    }

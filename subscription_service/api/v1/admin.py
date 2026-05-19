"""api/v1/admin.py — Platform owner (Riviwa admin) management endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
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


# ── Subscription monitoring ───────────────────────────────────────────────────

@router.get("/subscriptions/overview", summary="All orgs subscription status with renewal dates")
async def subscriptions_overview(
    db:            DbDep,
    _:             AdminDep,
    status:        Optional[str] = Query(default=None, description="active | trialing | past_due | paused | cancelled | expired"),
    plan_slug:     Optional[str] = Query(default=None, description="starter | professional | business | enterprise"),
    expiring_days: Optional[int] = Query(default=None, description="Only show subs renewing within N days"),
    page:          int = Query(default=1, ge=1),
    size:          int = Query(default=50, ge=1, le=100),
) -> dict:
    """
    Paginated list of all org subscriptions with plan, billing cycle, renewal date,
    days until renewal, and cancellation flag. Ideal for a live subscription
    monitoring dashboard. Filter by status, plan, or expiry horizon.
    """
    now = datetime.utcnow()
    q = select(Subscription, Plan).join(Plan, Plan.id == Subscription.plan_id)
    if status:
        q = q.where(Subscription.status == status)
    if plan_slug:
        q = q.where(Plan.slug == plan_slug)
    if expiring_days is not None:
        q = q.where(Subscription.current_period_end <= now + timedelta(days=expiring_days))

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    rows  = (await db.execute(
        q.order_by(Subscription.current_period_end.asc())
         .offset((page - 1) * size).limit(size)
    )).all()

    items = []
    for sub, plan in rows:
        days_left  = (sub.current_period_end - now).days
        hours_left = max(int((sub.current_period_end - now).total_seconds() / 3600), 0)
        items.append({
            "subscription_id":       str(sub.id),
            "org_id":                str(sub.org_id),
            "plan":                  {"slug": plan.slug, "display_name": plan.display_name},
            "billing_cycle":         sub.billing_cycle,
            "status":                sub.status,
            "current_period_start":  sub.current_period_start.isoformat(),
            "current_period_end":    sub.current_period_end.isoformat(),
            "days_until_renewal":    days_left,
            "hours_until_renewal":   hours_left,
            "cancel_at_period_end":  sub.cancel_at_period_end,
            "will_cancel":           sub.cancel_at_period_end,
            "effective_monthly_usd": str(sub.effective_monthly_usd),
            "discount_pct":          str(sub.discount_pct),
            "trial_end":             sub.trial_end.isoformat() if sub.trial_end else None,
            "created_at":            sub.created_at.isoformat(),
        })

    return {"total": total, "page": page, "size": size, "items": items}


@router.get("/subscriptions/due-soon", summary="Subscriptions renewing or expiring within N days")
async def subscriptions_due_soon(
    db:   DbDep,
    _:    AdminDep,
    days: int = Query(default=7, ge=1, le=90, description="Look-ahead window in days"),
) -> dict:
    """
    Returns all active/trialing subscriptions whose current period ends within
    the next N days. Splits results into 'renewing' (will auto-renew) and
    'cancelling' (cancel_at_period_end=true — org will lose access).
    Essential for proactive customer success outreach.
    """
    now    = datetime.utcnow()
    cutoff = now + timedelta(days=days)
    rows   = (await db.execute(
        select(Subscription, Plan)
        .join(Plan, Plan.id == Subscription.plan_id)
        .where(
            Subscription.status.in_(["active", "trialing", "past_due"]),
            Subscription.current_period_end >= now,
            Subscription.current_period_end <= cutoff,
        )
        .order_by(Subscription.current_period_end.asc())
    )).all()

    items = []
    for sub, plan in rows:
        days_left  = (sub.current_period_end - now).days
        hours_left = max(int((sub.current_period_end - now).total_seconds() / 3600), 0)
        items.append({
            "org_id":               str(sub.org_id),
            "subscription_id":      str(sub.id),
            "plan":                 plan.slug,
            "plan_display":         plan.display_name,
            "billing_cycle":        sub.billing_cycle,
            "status":               sub.status,
            "renews_at":            sub.current_period_end.isoformat(),
            "days_left":            days_left,
            "hours_left":           hours_left,
            "will_cancel":          sub.cancel_at_period_end,
            "effective_monthly_usd": str(sub.effective_monthly_usd),
        })

    renewing   = [i for i in items if not i["will_cancel"]]
    cancelling = [i for i in items if i["will_cancel"]]

    return {
        "horizon_days":     days,
        "total":            len(items),
        "renewing_count":   len(renewing),
        "cancelling_count": len(cancelling),
        "renewing":         renewing,
        "cancelling":       cancelling,
    }


@router.get("/subscriptions/by-plan", summary="Plan distribution — orgs per plan with MRR breakdown")
async def subscriptions_by_plan(db: DbDep, _: AdminDep) -> dict:
    """
    Counts active/trialing orgs per plan, broken down by billing cycle,
    with per-plan MRR contribution. Ordered by org count descending.
    """
    rows = (await db.execute(
        select(
            Plan.slug,
            Plan.display_name,
            Plan.monthly_price_usd,
            Plan.annual_price_usd,
            func.count(Subscription.id).label("total_orgs"),
            func.count(Subscription.id).filter(Subscription.status == "active").label("active"),
            func.count(Subscription.id).filter(Subscription.status == "trialing").label("trialing"),
            func.count(Subscription.id).filter(Subscription.status == "past_due").label("past_due"),
            func.count(Subscription.id).filter(Subscription.billing_cycle == "monthly").label("monthly_count"),
            func.count(Subscription.id).filter(Subscription.billing_cycle == "annual").label("annual_count"),
        )
        .join(Plan, Plan.id == Subscription.plan_id)
        .where(Subscription.status.in_(["active", "trialing", "past_due"]))
        .group_by(Plan.id, Plan.slug, Plan.display_name, Plan.monthly_price_usd, Plan.annual_price_usd)
        .order_by(func.count(Subscription.id).desc())
    )).all()

    by_plan = []
    total_orgs = 0
    total_mrr  = Decimal("0")
    for r in rows:
        mrr = (r.monthly_price_usd * r.monthly_count) + (r.annual_price_usd * r.annual_count)
        total_mrr  += mrr
        total_orgs += r.total_orgs
        by_plan.append({
            "plan":         r.slug,
            "display_name": r.display_name,
            "total_orgs":   r.total_orgs,
            "active":       r.active,
            "trialing":     r.trialing,
            "past_due":     r.past_due,
            "billing": {
                "monthly": r.monthly_count,
                "annual":  r.annual_count,
            },
            "mrr_usd":      str(mrr),
        })

    return {
        "total_orgs": total_orgs,
        "total_mrr_usd": str(total_mrr),
        "by_plan": by_plan,
    }

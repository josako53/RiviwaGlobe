"""api/v1/subscriptions.py — Org subscription lifecycle management."""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Query
from sqlalchemy import select, desc

from core.deps import DbDep, TokenDep, OrgIdDep, AdminDep, ServiceKeyDep
from core.exceptions import NotFoundError, PromoError, SubscriptionError, ValidationError
from services.subscription_svc import _now
from models.subscription import (
    AddOn, Invoice, InvoiceStatus, OrgAddOn, OrgFeatureOverride, OverrideType,
    PaymentMethod, PromoCode, PromoRedemption, Subscription, SubscriptionEvent,
    SubscriptionStatus, UsageMeter, Plan,
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


# ── Start trial ──────────────────────────────────────────────────────────────

@router.post("/trial", summary="Start a free trial", status_code=201)
async def start_trial(body: dict, db: DbDep, claims: TokenDep, org_id: OrgIdDep) -> dict:
    """
    Start a free trial for the organisation. Called automatically on first org creation
    or explicitly by the org admin.

    Body:
    {
      "plan_slug": "professional"   // optional, defaults to "professional"
    }

    Returns the new trialing subscription with trial end date.
    """
    svc = SubscriptionService(db)
    plan_slug = body.get("plan_slug", "professional")
    sub = await svc.start_trial(org_id, plan_slug=plan_slug)
    plan = await db.get(Plan, sub.plan_id)
    return {
        "subscription": _sub_out(sub, plan),
        "message": (
            f"{plan.trial_days}-day free trial started on {plan.display_name}. "
            f"Trial ends {sub.trial_end.strftime('%Y-%m-%d')}."
        ),
        "trial_end": sub.trial_end.isoformat(),
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


# ── Switch billing cycle ──────────────────────────────────────────────────────

@router.post("/switch-billing-cycle", summary="Switch between monthly and annual billing")
async def switch_billing_cycle(body: dict, db: DbDep, claims: TokenDep, org_id: OrgIdDep) -> dict:
    """
    Switch an active subscription between monthly and annual billing.

    - monthly → annual: charged the prorated annual price immediately.
      Annual pricing is ~20% cheaper. Saves money long-term.
    - annual → monthly: takes effect at next renewal (no refund).

    Body: { "billing_cycle": "annual" }   or   { "billing_cycle": "monthly" }
    """
    from models.subscription import BillingCycle
    from datetime import timedelta

    new_cycle = body.get("billing_cycle", "").lower()
    if new_cycle not in ("monthly", "annual"):
        raise ValidationError("billing_cycle must be 'monthly' or 'annual'.")

    svc = SubscriptionService(db)
    sub = await svc.get_org_subscription(org_id)
    if not sub:
        raise SubscriptionError("No active subscription found.")
    if sub.status not in (SubscriptionStatus.ACTIVE.value, SubscriptionStatus.TRIALING.value):
        raise SubscriptionError(f"Cannot switch billing cycle — subscription is {sub.status}.")
    if sub.billing_cycle == new_cycle:
        raise SubscriptionError(f"Subscription is already on {new_cycle} billing.")

    plan = await db.get(Plan, sub.plan_id)
    now  = _now()

    if new_cycle == "annual":
        # Switching to annual — charge prorated difference immediately
        days_remaining = max((sub.current_period_end - now).days, 0)
        monthly_rate   = plan.monthly_price_usd
        annual_monthly = plan.annual_price_usd
        # Credit for unused monthly days
        credit = monthly_rate * Decimal(days_remaining) / Decimal(30)
        # Annual charge (12 × annual monthly rate)
        annual_total = annual_monthly * 12
        amount_due   = max(annual_total - credit, Decimal("0"))

        sub.billing_cycle = "annual"
        sub.current_period_start = now
        sub.current_period_end   = now + timedelta(days=365)
        sub.effective_monthly_usd = annual_monthly
        sub.updated_at = now

        # Generate invoice only when there is a balance due
        invoice = None
        if amount_due > 0:
            invoice = await svc._generate_invoice(
                sub, plan, "monthly", sub.discount_pct,
                description=f"Switch to annual billing (credit ${credit:.2f} for unused days)",
                amount_override=amount_due,
            )
        await db.commit()
        return {
            "subscription":    _sub_out(sub, plan),
            "message":         "Switched to annual billing." + (" Invoice generated." if invoice else " No charge due."),
            "amount_due_usd":  str(amount_due),
            "invoice_number":  invoice.invoice_number if invoice else None,
            "new_period_end":  sub.current_period_end.isoformat(),
            "annual_savings_pct": 20,
        }
    else:
        # Switching to monthly — takes effect at next renewal
        sub.billing_cycle     = "monthly"
        sub.effective_monthly_usd = plan.monthly_price_usd
        sub.updated_at        = now
        await db.commit()
        return {
            "subscription": _sub_out(sub, plan),
            "message":      f"Switched to monthly billing. Takes effect at next renewal ({sub.current_period_end.isoformat()[:10]}).",
            "effective_at": sub.current_period_end.isoformat(),
        }


# ── Billing preview ───────────────────────────────────────────────────────────

@router.post("/billing-preview", summary="Preview exact cost before subscribing or changing plan")
async def billing_preview(body: dict, db: DbDep) -> dict:
    """
    Calculate the exact price for a plan before committing.
    Useful for checkout page order summary.

    Body:
    {
      "plan_id":       "uuid",
      "billing_cycle": "monthly" | "annual",
      "promo_code":    "RIVIWA50",     # optional
      "addons":        [{"slug": "extra-sms-1k", "quantity": 2}]  # optional
    }
    """
    from core.config import settings as cfg

    plan_id   = body.get("plan_id")
    cycle     = body.get("billing_cycle", "monthly")
    promo_code = body.get("promo_code", "").upper().strip()

    if not plan_id:
        raise ValidationError("plan_id is required.")

    plan = await db.get(Plan, uuid.UUID(plan_id))
    if not plan:
        raise NotFoundError("Plan")

    # Base price
    base_monthly = plan.annual_price_usd if cycle == "annual" else plan.monthly_price_usd
    base_total   = base_monthly * 12 if cycle == "annual" else base_monthly

    # Promo discount
    discount_amount = Decimal("0")
    promo_info = None
    if promo_code:
        promo = (await db.execute(
            select(PromoCode).where(PromoCode.code == promo_code, PromoCode.is_active == True)
        )).scalar_one_or_none()
        if promo:
            if promo.discount_type == "percentage":
                discount_amount = base_total * (promo.discount_value / 100)
            elif promo.discount_type == "fixed_amount":
                discount_amount = min(promo.discount_value, base_total)
            elif promo.discount_type == "free_months":
                discount_amount = base_monthly * promo.discount_value
            promo_info = {
                "code":    promo.code,
                "name":    promo.name,
                "label":   f"{promo.discount_value}{'%' if promo.discount_type == 'percentage' else ' USD'} off",
                "duration": promo.duration,
            }

    # Add-ons
    addon_total = Decimal("0")
    addon_lines = []
    for item in body.get("addons", []):
        addon = (await db.execute(
            select(AddOn).where(AddOn.slug == item.get("slug"), AddOn.is_active == True)
        )).scalar_one_or_none()
        if addon:
            qty      = max(int(item.get("quantity", 1)), 1)
            subtotal = addon.price_usd * qty
            addon_total += subtotal
            addon_lines.append({
                "slug": addon.slug, "name": addon.name,
                "unit_price_usd": str(addon.price_usd), "quantity": qty,
                "subtotal_usd":   str(subtotal),
            })

    subtotal = base_total - discount_amount + addon_total
    tax      = subtotal * cfg.TAX_RATE
    total    = subtotal + tax

    return {
        "plan":          {"id": str(plan.id), "slug": plan.slug, "display_name": plan.display_name},
        "billing_cycle": cycle,
        "line_items": [
            {"description": f"{plan.display_name} — {cycle.title()}", "amount_usd": str(base_total)},
            *(
                [{"description": f"Promo: {promo_info['name']}", "amount_usd": str(-discount_amount)}]
                if promo_info else []
            ),
            *addon_lines,
            {"description": f"VAT ({int(cfg.TAX_RATE * 100)}%)",    "amount_usd": str(tax)},
        ],
        "summary": {
            "subtotal_usd":   str(base_total + addon_total),
            "discount_usd":   str(discount_amount),
            "addon_total_usd": str(addon_total),
            "tax_usd":        str(tax),
            "total_usd":      str(total),
        },
        "promo":          promo_info,
        "trial_days":     plan.trial_days,
        "next_renewal":   f"{'annually' if cycle == 'annual' else 'monthly'} after trial",
    }


# ── Apply promo ───────────────────────────────────────────────────────────────

@router.post("/apply-promo", summary="Apply a promo code to existing subscription")
async def apply_promo(body: dict, db: DbDep, org_id: OrgIdDep) -> dict:
    svc = SubscriptionService(db)
    sub = await svc.get_org_subscription(org_id)
    if not sub:
        raise PromoError("No active subscription found.")
    plan = await db.get(Plan, sub.plan_id)
    promo, discount_pct, discount_months = await svc._validate_promo(
        body["code"], plan, org_id, new_subscriber=False
    )
    sub.promo_code_id = promo.id
    sub.discount_pct = discount_pct
    sub.discount_months_remaining = discount_months
    db.add(PromoRedemption(promo_code_id=promo.id, org_id=uuid.UUID(org_id), subscription_id=sub.id))
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
            "metadata": e.event_meta,
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

# ── My features (full entitlement map) ────────────────────────────────────────

@router.get("/my/features", summary="Get full feature entitlement map for my organisation")
async def my_features(db: DbDep, org_id: OrgIdDep) -> dict:
    """
    Returns every feature and limit entitlement for the authenticated org.
    Each feature shows: enabled, source (plan|override), and override reason.
    Each limit shows: plan_limit, effective_limit (after any override), used, pct_used.
    """
    svc = SubscriptionService(db)
    return await svc.get_org_entitlements(org_id)


# ── Internal: usage increment ─────────────────────────────────────────────────

@router.post("/internal/usage/increment", summary="Internal: increment a usage meter counter")
async def internal_usage_increment(body: dict, db: DbDep, _: ServiceKeyDep) -> dict:
    """
    Called by other services to track resource consumption.

    Body:
    {
      "org_id": "uuid",
      "metric": "submissions_count|sms_count|api_calls_count|storage_bytes|qr_codes_count",
      "amount": 1
    }
    """
    svc = SubscriptionService(db)
    await svc.increment_usage(
        org_id=body["org_id"],
        metric=body["metric"],
        amount=int(body.get("amount", 1)),
    )
    return {"ok": True, "org_id": body["org_id"], "metric": body["metric"]}


# ── Admin: org entitlements view ──────────────────────────────────────────────

@router.get("/admin/orgs/{org_id}/entitlements", summary="Admin: view full entitlement map for any org")
async def admin_org_entitlements(org_id: str, db: DbDep, _: AdminDep) -> dict:
    svc = SubscriptionService(db)
    return await svc.get_org_entitlements(org_id)


# ── Admin: grant / revoke / limit overrides ───────────────────────────────────

@router.post("/admin/orgs/{org_id}/overrides", summary="Admin: grant a feature or limit override to an org", status_code=201)
async def admin_grant_override(org_id: str, body: dict, db: DbDep, claims: AdminDep) -> dict:
    """
    Body:
    {
      "feature_key":   "sms_channel",
      "override_type": "grant" | "revoke" | "limit",
      "limit_value":   5000,
      "reason":        "NGO partnership deal",
      "note":          "Approved by CEO",
      "expires_at":    "2027-05-18T00:00:00"
    }
    """
    from datetime import datetime as dt

    feature_key   = body.get("feature_key", "").strip()
    override_type = body.get("override_type", "").lower()
    if not feature_key:
        raise ValidationError("feature_key is required.")
    if override_type not in ("grant", "revoke", "limit"):
        raise ValidationError("override_type must be grant, revoke, or limit.")
    if override_type == "limit" and body.get("limit_value") is None:
        raise ValidationError("limit_value is required when override_type=limit.")

    existing_ovs = (await db.execute(
        select(OrgFeatureOverride).where(
            OrgFeatureOverride.org_id == uuid.UUID(org_id),
            OrgFeatureOverride.feature_key == feature_key,
            OrgFeatureOverride.override_type == override_type,
            OrgFeatureOverride.is_active == True,
        )
    )).scalars().all()
    for ov in existing_ovs:
        ov.is_active = False

    expires_at = None
    if body.get("expires_at"):
        expires_at = dt.fromisoformat(body["expires_at"].replace("Z", "+00:00")).replace(tzinfo=None)

    override = OrgFeatureOverride(
        org_id        = uuid.UUID(org_id),
        feature_key   = feature_key,
        override_type = override_type,
        limit_value   = int(body["limit_value"]) if body.get("limit_value") is not None else None,
        reason        = body.get("reason"),
        note          = body.get("note"),
        granted_by    = uuid.UUID(claims.get("sub")) if claims.get("sub") else None,
        expires_at    = expires_at,
    )
    db.add(override)
    await db.commit()
    await db.refresh(override)

    return {
        "id":            str(override.id),
        "org_id":        org_id,
        "feature_key":   override.feature_key,
        "override_type": override.override_type,
        "limit_value":   override.limit_value,
        "reason":        override.reason,
        "note":          override.note,
        "expires_at":    override.expires_at.isoformat() if override.expires_at else None,
        "granted_by":    str(override.granted_by) if override.granted_by else None,
        "created_at":    override.created_at.isoformat(),
        "message":       f"Override {override_type!r} for {feature_key!r} granted to org {org_id}.",
    }


@router.patch("/admin/orgs/{org_id}/overrides/{override_id}", summary="Admin: update an override")
async def admin_update_override(org_id: str, override_id: str, body: dict, db: DbDep, _: AdminDep) -> dict:
    from datetime import datetime as dt
    ov = await db.get(OrgFeatureOverride, uuid.UUID(override_id))
    if not ov or str(ov.org_id) != org_id:
        raise NotFoundError("Override")
    for k in ("reason", "note", "limit_value", "is_active"):
        if k in body:
            setattr(ov, k, body[k])
    if "expires_at" in body:
        ov.expires_at = dt.fromisoformat(body["expires_at"].replace("Z", "+00:00")).replace(tzinfo=None) if body["expires_at"] else None
    ov.updated_at = dt.utcnow()
    await db.commit()
    return {
        "id":            str(ov.id),
        "feature_key":   ov.feature_key,
        "override_type": ov.override_type,
        "limit_value":   ov.limit_value,
        "reason":        ov.reason,
        "note":          ov.note,
        "is_active":     ov.is_active,
        "expires_at":    ov.expires_at.isoformat() if ov.expires_at else None,
        "updated_at":    ov.updated_at.isoformat(),
    }


@router.delete("/admin/orgs/{org_id}/overrides/{override_id}", summary="Admin: revoke an override")
async def admin_revoke_override(org_id: str, override_id: str, db: DbDep, _: AdminDep) -> dict:
    from datetime import datetime as _dt
    ov = await db.get(OrgFeatureOverride, uuid.UUID(override_id))
    if not ov or str(ov.org_id) != org_id:
        raise NotFoundError("Override")
    ov.is_active  = False
    ov.updated_at = _dt.utcnow()
    await db.commit()
    return {"message": f"Override {ov.feature_key!r} ({ov.override_type}) revoked.", "id": override_id}


@router.get("/admin/orgs/{org_id}/overrides", summary="Admin: list all overrides for an org")
async def admin_list_overrides(
    org_id: str, db: DbDep, _: AdminDep,
    active_only: bool = Query(default=True),
) -> dict:
    q = select(OrgFeatureOverride).where(OrgFeatureOverride.org_id == uuid.UUID(org_id))
    if active_only:
        q = q.where(OrgFeatureOverride.is_active == True)
    result = await db.execute(q.order_by(OrgFeatureOverride.created_at.desc()))
    overrides = list(result.scalars().all())
    return {
        "org_id":    org_id,
        "total":     len(overrides),
        "overrides": [
            {
                "id":            str(ov.id),
                "feature_key":   ov.feature_key,
                "override_type": ov.override_type,
                "limit_value":   ov.limit_value,
                "reason":        ov.reason,
                "note":          ov.note,
                "is_active":     ov.is_active,
                "expires_at":    ov.expires_at.isoformat() if ov.expires_at else None,
                "granted_by":    str(ov.granted_by) if ov.granted_by else None,
                "created_at":    ov.created_at.isoformat(),
            }
            for ov in overrides
        ],
    }

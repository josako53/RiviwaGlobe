"""api/v1/promotions.py — Full promotions, sales, and promo code management."""
from __future__ import annotations

import random
import string
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

import structlog
from fastapi import APIRouter, Query
from sqlalchemy import desc, func, select

from core.deps import AdminDep, DbDep, OrgIdDep, TokenDep
from core.exceptions import ConflictError, NotFoundError, PromoError, ValidationError
from models.subscription import (
    Plan, PromoCode, PromoRedemption, Subscription, SubscriptionStatus,
)

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/promotions", tags=["Promotions & Sales"])


# ── Serialisers ───────────────────────────────────────────────────────────────

def _promo_out(p: PromoCode, include_stats: bool = False) -> dict:
    out = {
        "id":                   str(p.id),
        "code":                 p.code,
        "name":                 p.name,
        "description":          p.description,
        "discount_type":        p.discount_type,
        "discount_value":       str(p.discount_value),
        "duration":             p.duration,
        "duration_months":      p.duration_months,
        "max_redemptions":      p.max_redemptions,
        "redemption_count":     p.redemption_count,
        "eligible_plans":       p.eligible_plans,
        "new_subscribers_only": p.new_subscribers_only,
        "min_plan_price_usd":   str(p.min_plan_price_usd),
        "expires_at":           p.expires_at.isoformat() if p.expires_at else None,
        "is_active":            p.is_active,
        "created_at":           p.created_at.isoformat(),
    }
    if include_stats:
        remaining = (
            p.max_redemptions - p.redemption_count
            if p.max_redemptions != -1
            else None
        )
        out["stats"] = {
            "redemptions_used":      p.redemption_count,
            "redemptions_remaining": remaining,
            "redemption_rate_pct":   (
                round(p.redemption_count / p.max_redemptions * 100, 1)
                if p.max_redemptions > 0 else None
            ),
            "is_expired": bool(p.expires_at and p.expires_at < datetime.utcnow()),
            "is_exhausted": (
                p.max_redemptions != -1 and p.redemption_count >= p.max_redemptions
            ),
        }
    return out


def _human_discount(p: PromoCode) -> str:
    if p.discount_type == "percentage":
        return f"{int(p.discount_value)}% off"
    if p.discount_type == "fixed_amount":
        return f"${p.discount_value} off"
    if p.discount_type == "free_months":
        return f"{int(p.discount_value)} free month(s)"
    return str(p.discount_value)


def _duration_label(p: PromoCode) -> str:
    if p.duration == "forever":     return "forever"
    if p.duration == "once":        return "first payment"
    if p.duration == "repeating":   return f"first {p.duration_months} month(s)"
    return p.duration


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("", summary="Active sales and promotions (public)")
async def list_active_promotions(
    db: DbDep,
    plan_slug: Optional[str] = Query(default=None, description="Filter by eligible plan"),
) -> dict:
    """
    Returns promotions that are currently active and publicly visible —
    i.e., valid, not expired, not exhausted. Ideal for pricing page banners.

    Does NOT expose promo codes — codes are revealed at checkout or sent via email.
    """
    now = datetime.utcnow()
    q = select(PromoCode).where(
        PromoCode.is_active == True,
        (PromoCode.expires_at == None) | (PromoCode.expires_at > now),
    )
    promos = (await db.execute(q.order_by(desc(PromoCode.created_at)))).scalars().all()

    # Filter out exhausted codes
    active = [
        p for p in promos
        if p.max_redemptions == -1 or p.redemption_count < p.max_redemptions
    ]

    # Filter by plan if requested
    if plan_slug:
        active = [
            p for p in active
            if not p.eligible_plans or plan_slug in (p.eligible_plans or [])
        ]

    return {
        "promotions": [
            {
                "name":           p.name,
                "description":    p.description,
                "discount_label": _human_discount(p),
                "duration_label": _duration_label(p),
                "eligible_plans": p.eligible_plans or "all",
                "expires_at":     p.expires_at.isoformat() if p.expires_at else None,
                "new_subscribers_only": p.new_subscribers_only,
            }
            for p in active
        ],
        "total": len(active),
    }


@router.post("/validate", summary="Validate a promo code and preview the discount")
async def validate_promo_code(body: dict, db: DbDep) -> dict:
    """
    Check if a promo code is valid for a given plan and show the exact discount.
    Does NOT apply the code — safe to call at any point during checkout.

    Body: { "code": "RIVIWA50", "plan_id": "uuid", "billing_cycle": "monthly" }
    """
    code      = body.get("code", "").strip().upper()
    plan_id   = body.get("plan_id")
    cycle     = body.get("billing_cycle", "monthly")
    org_id    = body.get("org_id")

    if not code:
        raise ValidationError("code is required.")

    # Find promo
    promo = (await db.execute(
        select(PromoCode).where(PromoCode.code == code)
    )).scalar_one_or_none()

    if not promo:
        return {"valid": False, "reason": "Promo code not found."}
    if not promo.is_active:
        return {"valid": False, "reason": "This promo code is no longer active."}

    now = datetime.utcnow()
    if promo.expires_at and promo.expires_at < now:
        return {"valid": False, "reason": "This promo code has expired.",
                "expired_at": promo.expires_at.isoformat()}
    if promo.max_redemptions != -1 and promo.redemption_count >= promo.max_redemptions:
        return {"valid": False, "reason": "This promo code has reached its maximum redemptions."}

    # Already used by this org?
    if org_id:
        used = (await db.execute(
            select(PromoRedemption).where(
                PromoRedemption.promo_code_id == promo.id,
                PromoRedemption.org_id == uuid.UUID(org_id),
            )
        )).scalar_one_or_none()
        if used:
            return {"valid": False, "reason": "You have already used this promo code."}

    # Fetch plan for price calculation
    plan = None
    if plan_id:
        plan = await db.get(Plan, uuid.UUID(plan_id))
        # Check plan eligibility
        if promo.eligible_plans and plan and plan.slug not in promo.eligible_plans:
            return {
                "valid":  False,
                "reason": f"This code is not valid for the {plan.display_name} plan.",
                "eligible_plans": promo.eligible_plans,
            }

    # Calculate discount preview
    base_price = Decimal("0")
    if plan:
        base_price = plan.annual_price_usd if cycle == "annual" else plan.monthly_price_usd
        if cycle == "annual":
            base_price = base_price * 12   # annual total

    discount_amount = Decimal("0")
    if promo.discount_type == "percentage":
        discount_amount = base_price * (promo.discount_value / 100)
    elif promo.discount_type == "fixed_amount":
        discount_amount = min(promo.discount_value, base_price)
    elif promo.discount_type == "free_months":
        monthly = plan.annual_price_usd if cycle == "annual" else (plan.monthly_price_usd if plan else Decimal("0"))
        discount_amount = monthly * promo.discount_value

    final_price = max(base_price - discount_amount, Decimal("0"))

    return {
        "valid":            True,
        "code":             promo.code,
        "name":             promo.name,
        "discount_type":    promo.discount_type,
        "discount_value":   str(promo.discount_value),
        "discount_label":   _human_discount(promo),
        "duration":         promo.duration,
        "duration_months":  promo.duration_months,
        "duration_label":   _duration_label(promo),
        "new_subscribers_only": promo.new_subscribers_only,
        "expires_at":       promo.expires_at.isoformat() if promo.expires_at else None,
        "pricing_preview":  {
            "base_price_usd":     str(base_price),
            "discount_usd":       str(discount_amount),
            "final_price_usd":    str(final_price),
            "billing_cycle":      cycle,
            "plan":               plan.display_name if plan else None,
        } if plan else None,
    }


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN — PROMO / SALES MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/admin", summary="Admin: list all promo codes with stats")
async def admin_list_promos(
    db: DbDep, _: AdminDep,
    active_only:  bool = Query(default=False),
    discount_type: Optional[str] = Query(default=None),
    plan_slug:    Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=50, ge=1, le=100),
) -> dict:
    q = select(PromoCode)
    if active_only:
        q = q.where(PromoCode.is_active == True)
    if discount_type:
        q = q.where(PromoCode.discount_type == discount_type)
    total  = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    promos = (await db.execute(
        q.order_by(desc(PromoCode.created_at)).offset((page - 1) * size).limit(size)
    )).scalars().all()

    # Revenue impact: sum of savings per redemption (approximation)
    return {
        "total": total, "page": page, "size": size,
        "promo_codes": [_promo_out(p, include_stats=True) for p in promos],
    }


@router.get("/admin/{promo_id}", summary="Admin: promo code detail with full stats")
async def admin_get_promo(promo_id: str, db: DbDep, _: AdminDep) -> dict:
    promo = await db.get(PromoCode, uuid.UUID(promo_id))
    if not promo:
        raise NotFoundError("Promo code")

    # Fetch redemptions
    redemptions = (await db.execute(
        select(PromoRedemption)
        .where(PromoRedemption.promo_code_id == promo.id)
        .order_by(desc(PromoRedemption.redeemed_at))
        .limit(20)
    )).scalars().all()

    out = _promo_out(promo, include_stats=True)
    out["recent_redemptions"] = [
        {
            "org_id":        str(r.org_id),
            "subscription_id": str(r.subscription_id),
            "redeemed_at":   r.redeemed_at.isoformat(),
        }
        for r in redemptions
    ]
    return out


@router.post("/admin", summary="Admin: create a promo code / sale", status_code=201)
async def admin_create_promo(body: dict, db: DbDep, claims: AdminDep) -> dict:
    """
    Create a promo code.

    discount_type:
      - "percentage"   → discount_value = 50 means 50% off
      - "fixed_amount" → discount_value = 20 means $20 off
      - "free_months"  → discount_value = 1 means 1 free month

    duration:
      - "once"       → applies to first payment only
      - "repeating"  → applies for duration_months payments
      - "forever"    → applies every billing cycle permanently

    Example — "First 3 months 50% off for new subscribers":
    {
      "code":                 "LAUNCH50",
      "name":                 "Launch Offer",
      "discount_type":        "percentage",
      "discount_value":       50,
      "duration":             "repeating",
      "duration_months":      3,
      "new_subscribers_only": true,
      "expires_at":           "2026-12-31T23:59:59"
    }
    """
    code = body.get("code", "").strip().upper()
    if not code:
        raise ValidationError("code is required.")

    existing = (await db.execute(
        select(PromoCode).where(PromoCode.code == code)
    )).scalar_one_or_none()
    if existing:
        raise ConflictError(f"Promo code '{code}' already exists.")

    discount_type = body.get("discount_type", "percentage")
    if discount_type not in ("percentage", "fixed_amount", "free_months"):
        raise ValidationError("discount_type must be: percentage | fixed_amount | free_months")

    duration = body.get("duration", "once")
    if duration not in ("once", "repeating", "forever"):
        raise ValidationError("duration must be: once | repeating | forever")

    promo = PromoCode(
        code                 = code,
        name                 = body.get("name", code),
        description          = body.get("description", ""),
        discount_type        = discount_type,
        discount_value       = Decimal(str(body.get("discount_value", 0))),
        duration             = duration,
        duration_months      = body.get("duration_months", 1),
        max_redemptions      = body.get("max_redemptions", -1),
        eligible_plans       = body.get("eligible_plans"),        # list of plan slugs or None = all
        new_subscribers_only = body.get("new_subscribers_only", False),
        min_plan_price_usd   = Decimal(str(body.get("min_plan_price_usd", 0))),
        expires_at           = datetime.fromisoformat(body["expires_at"]) if body.get("expires_at") else None,
        is_active            = body.get("is_active", True),
        created_by           = uuid.UUID(claims.get("sub")) if claims.get("sub") else None,
    )
    db.add(promo)
    await db.commit()
    await db.refresh(promo)
    log.info("promo.created", code=code, type=discount_type, value=str(promo.discount_value))
    return _promo_out(promo, include_stats=True)


@router.patch("/admin/{promo_id}", summary="Admin: update a promo code")
async def admin_update_promo(promo_id: str, body: dict, db: DbDep, _: AdminDep) -> dict:
    promo = await db.get(PromoCode, uuid.UUID(promo_id))
    if not promo:
        raise NotFoundError("Promo code")
    immutable = {"id", "code", "created_at", "redemption_count"}
    for k, v in body.items():
        if hasattr(promo, k) and k not in immutable:
            if k == "discount_value":    v = Decimal(str(v))
            if k == "expires_at" and v:  v = datetime.fromisoformat(v)
            setattr(promo, k, v)
    await db.commit()
    await db.refresh(promo)
    return _promo_out(promo, include_stats=True)


@router.delete("/admin/{promo_id}", summary="Admin: deactivate a promo code")
async def admin_deactivate_promo(promo_id: str, db: DbDep, _: AdminDep) -> dict:
    promo = await db.get(PromoCode, uuid.UUID(promo_id))
    if not promo:
        raise NotFoundError("Promo code")
    promo.is_active = False
    await db.commit()
    return {"message": f"Promo code '{promo.code}' deactivated.", "id": str(promo.id)}


@router.post("/admin/bulk-generate", summary="Admin: generate multiple unique promo codes", status_code=201)
async def admin_bulk_generate(body: dict, db: DbDep, claims: AdminDep) -> dict:
    """
    Generate N unique random promo codes with identical discount settings.
    Useful for email campaigns, partner codes, event giveaways.

    Body:
    {
      "prefix":              "NGO",        # e.g. NGO-XXXXX
      "count":               100,
      "discount_type":       "percentage",
      "discount_value":      30,
      "duration":            "once",
      "eligible_plans":      ["professional", "business"],
      "new_subscribers_only": true,
      "expires_at":          "2026-12-31T23:59:59",
      "name_prefix":         "NGO Partner Code"
    }
    """
    count  = min(int(body.get("count", 10)), 500)   # max 500 at a time
    prefix = body.get("prefix", "").upper().strip("-")
    codes  = []

    for _ in range(count):
        while True:
            rand   = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            code   = f"{prefix}-{rand}" if prefix else rand
            exists = (await db.execute(
                select(PromoCode).where(PromoCode.code == code)
            )).scalar_one_or_none()
            if not exists:
                break

        promo = PromoCode(
            code                 = code,
            name                 = f"{body.get('name_prefix', 'Promo')} — {code}",
            description          = body.get("description", ""),
            discount_type        = body.get("discount_type", "percentage"),
            discount_value       = Decimal(str(body.get("discount_value", 0))),
            duration             = body.get("duration", "once"),
            duration_months      = body.get("duration_months", 1),
            max_redemptions      = 1,   # each bulk code is single-use
            eligible_plans       = body.get("eligible_plans"),
            new_subscribers_only = body.get("new_subscribers_only", False),
            expires_at           = datetime.fromisoformat(body["expires_at"]) if body.get("expires_at") else None,
            is_active            = True,
            created_by           = uuid.UUID(claims.get("sub")) if claims.get("sub") else None,
        )
        db.add(promo)
        codes.append(code)

    await db.commit()
    log.info("promo.bulk_generated", count=count, prefix=prefix)
    return {
        "generated": count,
        "codes":     codes,
        "discount":  f"{body.get('discount_value')} {body.get('discount_type')}",
        "expires_at": body.get("expires_at"),
    }


@router.get("/admin/stats/summary", summary="Admin: promotions revenue impact summary")
async def admin_promo_stats(db: DbDep, _: AdminDep) -> dict:
    """Overall promotions stats: total codes, active codes, redemptions."""
    total      = (await db.execute(select(func.count(PromoCode.id)))).scalar_one()
    active     = (await db.execute(select(func.count(PromoCode.id)).where(PromoCode.is_active == True))).scalar_one()
    redemptions = (await db.execute(select(func.count(PromoRedemption.id)))).scalar_one()

    # Most redeemed
    top = (await db.execute(
        select(PromoCode).order_by(desc(PromoCode.redemption_count)).limit(5)
    )).scalars().all()

    # Expiring soon (next 7 days)
    from datetime import timedelta
    soon = datetime.utcnow() + timedelta(days=7)
    expiring = (await db.execute(
        select(PromoCode).where(
            PromoCode.is_active == True,
            PromoCode.expires_at != None,
            PromoCode.expires_at <= soon,
            PromoCode.expires_at > datetime.utcnow(),
        )
    )).scalars().all()

    return {
        "total_codes":       total,
        "active_codes":      active,
        "total_redemptions": redemptions,
        "top_codes": [
            {"code": p.code, "name": p.name, "redemptions": p.redemption_count}
            for p in top
        ],
        "expiring_soon": [
            {"code": p.code, "name": p.name, "expires_at": p.expires_at.isoformat()}
            for p in expiring
        ],
    }

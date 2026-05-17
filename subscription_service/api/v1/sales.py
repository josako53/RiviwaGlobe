"""api/v1/sales.py — Time-bounded sale campaigns with auto-apply and scheduling."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

import structlog
from fastapi import APIRouter, Query
from sqlalchemy import and_, desc, func, or_, select

from core.deps import AdminDep, DbDep, OrgIdDep
from core.exceptions import ConflictError, NotFoundError, ValidationError
from models.subscription import (
    Plan, PromoCode, Sale, SaleStatus, Subscription, SubscriptionStatus,
)

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/sales", tags=["Sales Campaigns"])

DISCOUNT_TYPES   = ("percentage", "fixed_amount", "free_months")
DURATION_TYPES   = ("once", "repeating", "forever")
BILLING_CYCLES   = ("monthly", "annual")


# ── Serialiser ────────────────────────────────────────────────────────────────

def _sale_out(s: Sale, include_admin: bool = False) -> dict:
    now = datetime.utcnow()
    remaining_secs = max(int((s.end_at - now).total_seconds()), 0) if s.is_currently_active else 0
    started_secs   = max(int((now - s.start_at).total_seconds()), 0) if s.status == SaleStatus.ACTIVE.value else 0
    starts_in_secs = max(int((s.start_at - now).total_seconds()), 0) if s.status == SaleStatus.SCHEDULED.value else 0

    out = {
        "id":           str(s.id),
        "name":         s.name,
        "description":  s.description,
        "banner_text":  s.banner_text,
        "status":       s.status,
        "schedule": {
            "start_at":        s.start_at.isoformat(),
            "end_at":          s.end_at.isoformat(),
            "starts_in_secs":  starts_in_secs,
            "remaining_secs":  remaining_secs,
            "duration_hours":  round((s.end_at - s.start_at).total_seconds() / 3600, 1),
        },
        "discount": {
            "type":            s.discount_type,
            "value":           str(s.discount_value),
            "label":           _discount_label(s),
            "duration":        s.duration,
            "duration_months": s.duration_months,
        },
        "targeting": {
            "eligible_plans":          s.eligible_plans or "all",
            "eligible_billing_cycles": s.eligible_billing_cycles or "all",
            "new_subscribers_only":    s.new_subscribers_only,
        },
        "auto_apply":    s.auto_apply,
        "is_active":     s.is_currently_active,
    }
    if include_admin:
        out["limits"] = {
            "max_redemptions":  s.max_redemptions,
            "redemption_count": s.redemption_count,
            "remaining":        (
                s.max_redemptions - s.redemption_count
                if s.max_redemptions != -1 else None
            ),
        }
        out["promo_code_id"] = str(s.promo_code_id) if s.promo_code_id else None
        out["created_at"]    = s.created_at.isoformat()
        out["updated_at"]    = s.updated_at.isoformat()
    return out


def _discount_label(s: Sale) -> str:
    if s.discount_type == "percentage":
        return f"{int(s.discount_value)}% off"
    if s.discount_type == "fixed_amount":
        return f"${s.discount_value} off"
    if s.discount_type == "free_months":
        return f"{int(s.discount_value)} free month(s)"
    return str(s.discount_value)


def _active_sale_filter():
    now = datetime.utcnow()
    return and_(
        Sale.is_active == True,
        Sale.start_at  <= now,
        Sale.end_at    >= now,
    )


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("", summary="Active and upcoming sales (public)")
async def list_sales(
    db:        DbDep,
    plan_slug: Optional[str] = Query(default=None, description="Filter by eligible plan slug"),
    cycle:     Optional[str] = Query(default=None, description="Filter by billing cycle"),
    include_upcoming: bool   = Query(default=True, description="Include scheduled (future) sales"),
) -> dict:
    """
    Returns currently active sales and optionally upcoming (scheduled) ones.
    Safe to call publicly — does not expose admin-only fields.
    Ideal for pricing page banners and checkout discount notices.
    """
    now = datetime.utcnow()

    if include_upcoming:
        q = select(Sale).where(Sale.is_active == True, Sale.end_at >= now)
    else:
        q = select(Sale).where(_active_sale_filter())

    sales = (await db.execute(q.order_by(Sale.start_at))).scalars().all()

    # Filter out exhausted sales
    sales = [s for s in sales if s.max_redemptions == -1 or s.redemption_count < s.max_redemptions]

    # Filter by plan
    if plan_slug:
        sales = [s for s in sales if not s.eligible_plans or plan_slug in (s.eligible_plans or [])]

    # Filter by billing cycle
    if cycle:
        sales = [s for s in sales if not s.eligible_billing_cycles or cycle in (s.eligible_billing_cycles or [])]

    active    = [s for s in sales if s.status == SaleStatus.ACTIVE.value]
    upcoming  = [s for s in sales if s.status == SaleStatus.SCHEDULED.value]

    return {
        "active_sales":   [_sale_out(s) for s in active],
        "upcoming_sales": [_sale_out(s) for s in upcoming] if include_upcoming else [],
        "has_active_sale": len(active) > 0,
    }


@router.get("/current", summary="Get the best active sale for a given plan")
async def current_best_sale(
    db:        DbDep,
    plan_slug: Optional[str] = Query(default=None),
    cycle:     Optional[str] = Query(default="monthly"),
) -> dict:
    """
    Returns the single best (highest discount) active sale applicable to
    a given plan + billing cycle. Used by checkout to auto-apply the best deal.
    """
    sales = (await db.execute(
        select(Sale).where(_active_sale_filter())
    )).scalars().all()

    # Filter
    applicable = [
        s for s in sales
        if (not s.eligible_plans or not plan_slug or plan_slug in (s.eligible_plans or []))
        and (not s.eligible_billing_cycles or not cycle or cycle in (s.eligible_billing_cycles or []))
        and (s.max_redemptions == -1 or s.redemption_count < s.max_redemptions)
    ]

    if not applicable:
        return {"sale": None, "has_sale": False}

    # Pick highest discount (percentage first, then fixed)
    def _score(s: Sale) -> float:
        if s.discount_type == "percentage":   return float(s.discount_value) * 1000
        if s.discount_type == "fixed_amount": return float(s.discount_value)
        return float(s.discount_value) * 100   # free_months

    best = max(applicable, key=_score)
    return {"sale": _sale_out(best), "has_sale": True}


@router.get("/{sale_id}", summary="Get sale detail")
async def get_sale(sale_id: str, db: DbDep) -> dict:
    sale = await db.get(Sale, uuid.UUID(sale_id))
    if not sale or not sale.is_active:
        raise NotFoundError("Sale")
    return _sale_out(sale)


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN — SALE MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/admin/all", summary="Admin: list all sales by status")
async def admin_list_sales(
    db:     DbDep,
    _:      AdminDep,
    status: Optional[str] = Query(default=None, description="scheduled | active | ended | cancelled"),
    page:   int = Query(default=1, ge=1),
    size:   int = Query(default=50, ge=1, le=100),
) -> dict:
    now = datetime.utcnow()
    q   = select(Sale)

    if status == "scheduled":
        q = q.where(Sale.is_active == True,  Sale.start_at > now)
    elif status == "active":
        q = q.where(Sale.is_active == True,  Sale.start_at <= now, Sale.end_at >= now)
    elif status == "ended":
        q = q.where(Sale.is_active == True,  Sale.end_at < now)
    elif status == "cancelled":
        q = q.where(Sale.is_active == False)

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    sales = (await db.execute(
        q.order_by(desc(Sale.start_at)).offset((page - 1) * size).limit(size)
    )).scalars().all()

    return {
        "total": total, "page": page, "size": size,
        "sales": [_sale_out(s, include_admin=True) for s in sales],
    }


@router.post("/admin", summary="Admin: create a sale campaign", status_code=201)
async def admin_create_sale(body: dict, db: DbDep, claims: AdminDep) -> dict:
    """
    Create a time-bounded sale campaign.

    Required: name, start_at, end_at, discount_type, discount_value

    Examples:

    Flash sale — 40% off all plans for 24 hours:
    {
      "name":            "Flash Friday",
      "banner_text":     "⚡ Flash Sale — 40% off ends tonight!",
      "start_at":        "2026-06-01T00:00:00",
      "end_at":          "2026-06-01T23:59:59",
      "discount_type":   "percentage",
      "discount_value":  40,
      "duration":        "once",
      "auto_apply":      true
    }

    Seasonal sale — 30% off Business for 1 week, new subscribers only:
    {
      "name":                "World GRM Day Sale",
      "start_at":            "2026-06-15T00:00:00",
      "end_at":              "2026-06-22T23:59:59",
      "discount_type":       "percentage",
      "discount_value":      30,
      "duration":            "repeating",
      "duration_months":     3,
      "eligible_plans":      ["business"],
      "new_subscribers_only": true,
      "auto_apply":          false,
      "generate_code":       true,
      "code_prefix":         "GRM"
    }
    """
    # Validate
    if not body.get("name"):
        raise ValidationError("name is required.")
    start_at = _parse_dt(body.get("start_at"))
    end_at   = _parse_dt(body.get("end_at"))
    if not start_at or not end_at:
        raise ValidationError("start_at and end_at are required (ISO 8601).")
    if end_at <= start_at:
        raise ValidationError("end_at must be after start_at.")
    if body.get("discount_type") not in DISCOUNT_TYPES:
        raise ValidationError(f"discount_type must be one of: {DISCOUNT_TYPES}")
    if body.get("duration", "once") not in DURATION_TYPES:
        raise ValidationError(f"duration must be one of: {DURATION_TYPES}")

    billing_cycles = body.get("eligible_billing_cycles")
    if billing_cycles and not all(c in BILLING_CYCLES for c in billing_cycles):
        raise ValidationError(f"billing cycles must be from: {BILLING_CYCLES}")

    sale = Sale(
        name            = body["name"],
        description     = body.get("description", ""),
        banner_text     = body.get("banner_text", ""),
        start_at        = start_at,
        end_at          = end_at,
        discount_type   = body["discount_type"],
        discount_value  = Decimal(str(body.get("discount_value", 0))),
        duration        = body.get("duration", "once"),
        duration_months = body.get("duration_months", 1),
        eligible_plans  = body.get("eligible_plans"),
        eligible_billing_cycles = billing_cycles,
        new_subscribers_only    = body.get("new_subscribers_only", False),
        max_redemptions = body.get("max_redemptions", -1),
        auto_apply      = body.get("auto_apply", True),
        is_active       = True,
        created_by      = uuid.UUID(claims.get("sub")) if claims.get("sub") else None,
    )

    # Optionally auto-generate a promo code for sharing
    if body.get("generate_code", False):
        import random, string
        prefix = body.get("code_prefix", "SALE").upper()
        rand   = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        code   = f"{prefix}-{rand}"
        promo  = PromoCode(
            code                 = code,
            name                 = sale.name,
            description          = sale.description,
            discount_type        = sale.discount_type,
            discount_value       = sale.discount_value,
            duration             = sale.duration,
            duration_months      = sale.duration_months,
            max_redemptions      = sale.max_redemptions,
            eligible_plans       = sale.eligible_plans,
            new_subscribers_only = sale.new_subscribers_only,
            expires_at           = end_at,
            is_active            = True,
            created_by           = sale.created_by,
        )
        db.add(promo)
        await db.flush()
        sale.promo_code_id = promo.id

    db.add(sale)
    await db.commit()
    await db.refresh(sale)
    log.info("sale.created", id=str(sale.id), name=sale.name,
             start=start_at.isoformat(), end=end_at.isoformat())
    return _sale_out(sale, include_admin=True)


@router.patch("/admin/{sale_id}", summary="Admin: update a sale (schedule, discount, targeting)")
async def admin_update_sale(sale_id: str, body: dict, db: DbDep, _: AdminDep) -> dict:
    """
    Update any sale field. Can reschedule, change discount, or update targeting.
    Cannot update a sale that has already ended.
    """
    sale = await db.get(Sale, uuid.UUID(sale_id))
    if not sale:
        raise NotFoundError("Sale")
    if sale.status == SaleStatus.ENDED.value:
        raise ValidationError("Cannot update a sale that has already ended.")

    immutable = {"id", "created_at", "created_by", "redemption_count"}
    for k, v in body.items():
        if k in immutable:
            continue
        if k in ("start_at", "end_at") and v:
            v = _parse_dt(v)
        if k == "discount_value" and v is not None:
            v = Decimal(str(v))
        if hasattr(sale, k):
            setattr(sale, k, v)

    # Validate dates after update
    if sale.end_at <= sale.start_at:
        raise ValidationError("end_at must be after start_at.")

    sale.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(sale)
    return _sale_out(sale, include_admin=True)


@router.post("/admin/{sale_id}/activate", summary="Admin: manually activate a sale immediately")
async def admin_activate_sale(sale_id: str, db: DbDep, _: AdminDep) -> dict:
    """Force-start a scheduled sale right now by moving start_at to the current time."""
    sale = await db.get(Sale, uuid.UUID(sale_id))
    if not sale:
        raise NotFoundError("Sale")
    if sale.status == SaleStatus.CANCELLED.value:
        raise ValidationError("Cannot activate a cancelled sale.")
    if sale.status == SaleStatus.ENDED.value:
        raise ValidationError("Sale has already ended.")

    now = datetime.utcnow()
    sale.start_at   = now
    sale.is_active  = True
    sale.updated_at = now
    await db.commit()
    log.info("sale.manually_activated", id=str(sale.id))
    return {**_sale_out(sale, include_admin=True),
            "message": f"Sale '{sale.name}' is now active."}


@router.post("/admin/{sale_id}/end", summary="Admin: manually end a sale immediately")
async def admin_end_sale(sale_id: str, db: DbDep, _: AdminDep) -> dict:
    """Force-stop a running sale by moving end_at to the current time."""
    sale = await db.get(Sale, uuid.UUID(sale_id))
    if not sale:
        raise NotFoundError("Sale")
    if not sale.is_active:
        raise ValidationError("Sale is already cancelled or ended.")

    now = datetime.utcnow()
    sale.end_at     = now
    sale.updated_at = now
    await db.commit()
    log.info("sale.manually_ended", id=str(sale.id))
    return {**_sale_out(sale, include_admin=True),
            "message": f"Sale '{sale.name}' ended."}


@router.delete("/admin/{sale_id}", summary="Admin: cancel a sale")
async def admin_cancel_sale(sale_id: str, db: DbDep, _: AdminDep) -> dict:
    """Cancel a sale (scheduled or active). Cannot cancel an already-ended sale."""
    sale = await db.get(Sale, uuid.UUID(sale_id))
    if not sale:
        raise NotFoundError("Sale")
    if sale.status == SaleStatus.ENDED.value:
        raise ValidationError("Sale has already ended and cannot be cancelled.")

    sale.is_active  = False
    sale.updated_at = datetime.utcnow()
    await db.commit()
    log.info("sale.cancelled", id=str(sale.id))
    return {"message": f"Sale '{sale.name}' cancelled.", "id": str(sale.id)}


@router.post("/admin/{sale_id}/extend", summary="Admin: extend a sale's end date")
async def admin_extend_sale(sale_id: str, body: dict, db: DbDep, _: AdminDep) -> dict:
    """
    Extend a sale by a number of hours or to a specific new end_at.

    Body: { "hours": 24 }   or   { "end_at": "2026-06-10T23:59:59" }
    """
    sale = await db.get(Sale, uuid.UUID(sale_id))
    if not sale:
        raise NotFoundError("Sale")
    if sale.status == SaleStatus.CANCELLED.value:
        raise ValidationError("Cannot extend a cancelled sale.")

    if body.get("hours"):
        sale.end_at += timedelta(hours=int(body["hours"]))
    elif body.get("end_at"):
        new_end = _parse_dt(body["end_at"])
        if new_end <= sale.end_at:
            raise ValidationError("New end_at must be after current end_at.")
        sale.end_at = new_end
    else:
        raise ValidationError("Provide 'hours' or 'end_at'.")

    sale.updated_at = datetime.utcnow()
    await db.commit()
    log.info("sale.extended", id=str(sale.id), new_end=sale.end_at.isoformat())
    return {**_sale_out(sale, include_admin=True),
            "message": f"Sale extended to {sale.end_at.isoformat()}."}


@router.get("/admin/{sale_id}/stats", summary="Admin: sale performance stats")
async def admin_sale_stats(sale_id: str, db: DbDep, _: AdminDep) -> dict:
    """Redemption count, revenue impact, time remaining."""
    sale = await db.get(Sale, uuid.UUID(sale_id))
    if not sale:
        raise NotFoundError("Sale")

    now             = datetime.utcnow()
    total_duration  = (sale.end_at - sale.start_at).total_seconds()
    elapsed         = max((now - sale.start_at).total_seconds(), 0)
    progress_pct    = min(round(elapsed / total_duration * 100, 1), 100) if total_duration > 0 else 0
    remaining_secs  = max(int((sale.end_at - now).total_seconds()), 0)

    return {
        "id":               str(sale.id),
        "name":             sale.name,
        "status":           sale.status,
        "redemption_count": sale.redemption_count,
        "max_redemptions":  sale.max_redemptions,
        "slots_remaining":  (
            sale.max_redemptions - sale.redemption_count
            if sale.max_redemptions != -1 else None
        ),
        "schedule": {
            "start_at":       sale.start_at.isoformat(),
            "end_at":         sale.end_at.isoformat(),
            "progress_pct":   progress_pct,
            "remaining_secs": remaining_secs,
            "remaining_human": _human_time(remaining_secs),
        },
        "discount": {
            "type":  sale.discount_type,
            "value": str(sale.discount_value),
            "label": _discount_label(sale),
        },
    }


# ══════════════════════════════════════════════════════════════════════════════
# INTERNAL — apply active sale at checkout
# ══════════════════════════════════════════════════════════════════════════════

async def get_best_auto_apply_sale(
    db:        object,
    plan_slug: str,
    cycle:     str,
    new_subscriber: bool,
) -> Optional[Sale]:
    """
    Called by checkout.py to find the best active auto-apply sale.
    Returns the sale with the highest discount, or None.
    """
    sales = (await db.execute(
        select(Sale).where(
            Sale.is_active == True,
            Sale.auto_apply == True,
            Sale.start_at <= datetime.utcnow(),
            Sale.end_at   >= datetime.utcnow(),
        )
    )).scalars().all()

    applicable = [
        s for s in sales
        if (not s.eligible_plans or plan_slug in (s.eligible_plans or []))
        and (not s.eligible_billing_cycles or cycle in (s.eligible_billing_cycles or []))
        and (not s.new_subscribers_only or new_subscriber)
        and (s.max_redemptions == -1 or s.redemption_count < s.max_redemptions)
    ]

    if not applicable:
        return None

    def _score(s: Sale) -> float:
        if s.discount_type == "percentage":   return float(s.discount_value) * 1000
        if s.discount_type == "fixed_amount": return float(s.discount_value)
        return float(s.discount_value) * 100

    return max(applicable, key=_score)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        raise ValidationError(f"Invalid datetime format: '{value}'. Use ISO 8601 e.g. 2026-06-01T00:00:00")


def _human_time(seconds: int) -> str:
    if seconds <= 0:       return "Ended"
    if seconds < 60:       return f"{seconds}s"
    if seconds < 3600:     return f"{seconds // 60}m {seconds % 60}s"
    if seconds < 86400:    return f"{seconds // 3600}h {(seconds % 3600) // 60}m"
    days  = seconds // 86400
    hours = (seconds % 86400) // 3600
    return f"{days}d {hours}h"

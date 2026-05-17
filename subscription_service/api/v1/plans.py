"""api/v1/plans.py — Public plan listing and detail."""
from __future__ import annotations
import uuid
from typing import Optional
from fastapi import APIRouter, Query
from core.deps import DbDep, OptTokenDep, AdminDep
from core.exceptions import NotFoundError
from models.subscription import AddOn, Plan
from services.subscription_svc import SubscriptionService
from sqlalchemy import select

router = APIRouter(prefix="/plans", tags=["Plans"])


def _plan_out(p: Plan, include_admin: bool = False) -> dict:
    out = {
        "id": str(p.id),
        "slug": p.slug,
        "display_name": p.display_name,
        "tagline": p.tagline,
        "description": p.description,
        "pricing": {
            "monthly_usd": str(p.monthly_price_usd),
            "annual_usd":  str(p.annual_price_usd),
            "annual_monthly_usd": str(p.annual_price_usd),
            "annual_savings_pct": 20,
            "is_custom": p.is_custom,
        },
        "trial_days": p.trial_days,
        "limits": {
            "team_members":         p.max_team_members,
            "projects":             p.max_projects,
            "submissions_per_month": p.max_submissions_per_month,
            "sms_per_month":        p.max_sms_per_month,
            "api_calls_per_month":  p.max_api_calls_per_month,
            "storage_gb":           p.max_storage_gb,
            "qr_per_month":         p.max_qr_per_month,
            "staff_profiles":       p.max_staff_profiles,
        },
        "features": {
            # ── Feedback channels ──────────────────────────────────────
            "sms_channel":             p.has_sms_channel,
            "whatsapp_channel":        p.has_whatsapp_channel,
            "phone_call_ai":           p.has_phone_call_ai,
            # ── AI & Intelligence ──────────────────────────────────────
            "ai_conversation":         p.has_ai_conversation,
            "ai_insights":             p.has_ai_insights,
            "voice_transcription":     p.has_voice_transcription,
            "ml_escalation_predictor": p.has_ml_predictor,
            "spark_streaming":         p.has_spark_streaming,
            "recommendations":         getattr(p, "has_recommendations", False),
            # ── Notifications ──────────────────────────────────────────
            "push_notifications":      p.has_push_notifications,
            "whatsapp_notifications":  p.has_whatsapp_notif,
            # ── Analytics ─────────────────────────────────────────────
            "advanced_analytics":      p.has_advanced_analytics,
            "custom_reports":          p.has_custom_reports,
            # ── Feedback management ────────────────────────────────────
            "employee_feedback":       p.has_employee_feedback,
            "pap_registry":            p.has_pap_registry,
            "committee_management":    p.has_committee_mgmt,
            "bulk_import":             p.has_bulk_import,
            # ── QR & Verification ─────────────────────────────────────
            "qr_generation":           p.has_qr_generation,
            "product_verification":    p.has_product_verification,
            "ai_counterfeit_analysis": p.has_ai_counterfeit,
            "field_agents":            p.has_field_agents,
            # ── Staff service ─────────────────────────────────────────
            "staff_verification":      p.has_staff_verification,
            "bulk_staff_import":       getattr(p, "has_bulk_staff_import", False),
            "staff_analytics":         getattr(p, "has_staff_analytics", False),
            # ── Queue management ──────────────────────────────────────
            "waiting_queue":           getattr(p, "has_waiting_queue", False),
            # ── Stakeholder ───────────────────────────────────────────
            "stakeholder_engagement":  p.has_stakeholder_engagement,
            # ── Translation ───────────────────────────────────────────
            "translation_63_languages": p.has_translation,
            "advanced_translation":    getattr(p, "has_advanced_translation", False),
            # ── Product catalog ───────────────────────────────────────
            "product_catalog":         getattr(p, "has_product_catalog", False),
            "product_variations":      getattr(p, "has_product_variations", False),
            "rsin":                    getattr(p, "has_rsin", False),
            # ── Integration ───────────────────────────────────────────
            "api_access":              p.has_api_access,
            "webhooks":                p.has_webhooks,
            "oauth2":                  p.has_oauth2,
            "widget_embed":            p.has_widget_embed,
            "audit_logs":              getattr(p, "has_audit_logs", False),
            # ── Payment ───────────────────────────────────────────────
            "mobile_money_payments":   getattr(p, "has_mobile_money", False),
            "paypal_payments":         getattr(p, "has_paypal", False),
            # ── Auth extended ─────────────────────────────────────────
            "social_login":            getattr(p, "has_social_login", False),
            "id_verification":         getattr(p, "has_id_verification", False),
            "fraud_detection":         getattr(p, "has_fraud_detection", False),
            "multi_org":               getattr(p, "has_multi_org", False),
            "two_factor_auth":         p.has_2fa,
            "sso":                     p.has_sso,
            # ── Platform ─────────────────────────────────────────────
            "white_label":             p.has_white_label,
            "dedicated_support":       p.has_dedicated_support,
            "custom_sla":              p.has_custom_sla,
        },
        "sla": p.uptime_sla,
        "sort_order": p.sort_order,
    }
    if include_admin:
        out["is_active"] = p.is_active
        out["is_public"] = p.is_public
    return out


@router.get("", summary="List all public plans")
async def list_plans(db: DbDep) -> dict:
    svc = SubscriptionService(db)
    plans = await svc.list_plans()
    return {"plans": [_plan_out(p) for p in plans]}


@router.get("/{plan_id_or_slug}", summary="Get plan detail")
async def get_plan(plan_id_or_slug: str, db: DbDep) -> dict:
    svc = SubscriptionService(db)
    try:
        uuid.UUID(plan_id_or_slug)
        plan = await svc.get_plan(plan_id_or_slug)
    except ValueError:
        plan = await svc.get_plan_by_slug(plan_id_or_slug)
    return _plan_out(plan)


@router.get("/admin/all", summary="Admin: list all plans including inactive")
async def admin_list_plans(db: DbDep, _: AdminDep) -> dict:
    result = await db.execute(select(Plan).order_by(Plan.sort_order))
    plans = list(result.scalars().all())
    return {"plans": [_plan_out(p, include_admin=True) for p in plans]}


@router.post("/admin", summary="Admin: create a plan", status_code=201)
async def admin_create_plan(body: dict, db: DbDep, _: AdminDep) -> dict:
    plan = Plan(**{k: v for k, v in body.items() if hasattr(Plan, k)})
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return _plan_out(plan, include_admin=True)


@router.patch("/admin/{plan_id}", summary="Admin: update a plan")
async def admin_update_plan(plan_id: str, body: dict, db: DbDep, _: AdminDep) -> dict:
    plan = await db.get(Plan, uuid.UUID(plan_id))
    if not plan:
        raise NotFoundError("Plan")
    for k, v in body.items():
        if hasattr(plan, k) and k not in ("id", "created_at"):
            setattr(plan, k, v)
    from datetime import datetime
    plan.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(plan)
    return _plan_out(plan, include_admin=True)


# ── Add-ons ───────────────────────────────────────────────────────────────────

@router.get("/addons/list", summary="List available add-ons")
async def list_addons(db: DbDep) -> dict:
    result = await db.execute(select(AddOn).where(AddOn.is_active == True))
    addons = list(result.scalars().all())
    return {"addons": [
        {
            "id": str(a.id), "slug": a.slug, "name": a.name,
            "description": a.description, "type": a.type,
            "price_usd": str(a.price_usd), "unit": a.unit, "unit_quantity": a.unit_quantity,
        }
        for a in addons
    ]}

"""api/v1/plans.py — Full plan, feature, and add-on management."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Query
from sqlalchemy import select

from core.deps import AdminDep, DbDep, OptTokenDep
from core.exceptions import ConflictError, NotFoundError, ValidationError
from models.subscription import AddOn, Plan
from services.subscription_svc import SubscriptionService

router = APIRouter(prefix="/plans", tags=["Plans"])

# ── Feature catalog — every feature in the Riviwa platform ───────────────────
# Grouped by service. The key matches the `has_<key>` field on Plan model.

FEATURE_CATALOG = [
    # ── Feedback channels (feedback_service) ──────────────────────────────────
    {"key": "sms_channel",            "category": "Feedback Channels",    "label": "SMS Channel",                    "description": "Receive feedback via inbound SMS. Supports all Tanzanian networks via Karibu OTP API.",          "service": "feedback_service"},
    {"key": "whatsapp_channel",       "category": "Feedback Channels",    "label": "WhatsApp Channel",               "description": "Receive feedback via WhatsApp. Uses Meta Cloud API with AI conversation support.",               "service": "feedback_service"},
    {"key": "phone_call_ai",          "category": "Feedback Channels",    "label": "Phone Call AI (IVR)",            "description": "Fully AI-driven phone call feedback collection. Twilio + TTS/STT pipeline.",                      "service": "ai_service"},
    # ── AI & Intelligence (ai_service) ───────────────────────────────────────
    {"key": "ai_conversation",        "category": "AI & Intelligence",    "label": "AI Conversation (Web/Mobile)",   "description": "Guided AI dialogue on web and mobile. Auto-submits feedback at confidence ≥ 0.82.",                "service": "ai_service"},
    {"key": "ai_insights",            "category": "AI & Intelligence",    "label": "AI-Powered Insights",            "description": "Groq-powered natural language analysis of feedback patterns and root causes.",                    "service": "analytics_service"},
    {"key": "voice_transcription",    "category": "AI & Intelligence",    "label": "Voice Transcription",            "description": "Submit audio feedback. Transcribed via Whisper or Google STT with multi-language support.",       "service": "ai_service"},
    {"key": "ml_predictor",           "category": "AI & Intelligence",    "label": "ML Escalation Predictor",        "description": "Machine learning model predicts escalation risk before issues become critical.",                   "service": "analytics_service"},
    {"key": "spark_streaming",        "category": "AI & Intelligence",    "label": "Real-Time Spark Streaming",      "description": "Live SLA monitor, hotspot detector, and dashboard powered by Apache Spark streaming jobs.",       "service": "analytics_service"},
    {"key": "recommendations",        "category": "AI & Intelligence",    "label": "Smart Recommendations",          "description": "4-signal scoring: semantic (35%), tag overlap (25%), geo proximity (25%), recency (15%).",         "service": "recommendation_service"},
    {"key": "ai_counterfeit",         "category": "AI & Intelligence",    "label": "AI Counterfeit Analysis",        "description": "CLIP + Llama 4 Scout vision model analyses suspected fake product photos.",                       "service": "verification_service"},
    # ── Notifications (notification_service) ─────────────────────────────────
    {"key": "push_notifications",     "category": "Notifications",        "label": "Push Notifications",             "description": "Mobile push via Firebase Admin SDK. Supports iOS and Android.",                                  "service": "notification_service"},
    {"key": "whatsapp_notif",         "category": "Notifications",        "label": "WhatsApp Notifications",         "description": "Outbound WhatsApp messages for status updates, OTPs, and receipts.",                             "service": "notification_service"},
    # ── Analytics (analytics_service) ────────────────────────────────────────
    {"key": "advanced_analytics",     "category": "Analytics",            "label": "Advanced Analytics Dashboard",   "description": "KPI calculations, SLA tracking, response time, resolution rate, branch/department breakdown.",   "service": "analytics_service"},
    {"key": "custom_reports",         "category": "Analytics",            "label": "Custom Report Builder",          "description": "Build and schedule custom reports. Export as PDF or CSV.",                                      "service": "analytics_service"},
    # ── Feedback management (feedback_service) ────────────────────────────────
    {"key": "employee_feedback",      "category": "Feedback Management",  "label": "Employee Feedback (360°)",       "description": "Post-staff-verification 4-type employee feedback with 12 categories.",                           "service": "feedback_service"},
    {"key": "pap_registry",           "category": "Feedback Management",  "label": "PAP Registry",                   "description": "Project Affected Persons registry linked to feedback and escalation flows.",                    "service": "feedback_service"},
    {"key": "committee_mgmt",         "category": "Feedback Management",  "label": "Committee Management",           "description": "Configure review committees for grievance adjudication.",                                      "service": "feedback_service"},
    {"key": "bulk_import",            "category": "Feedback Management",  "label": "Bulk Feedback Import",           "description": "Import historical feedback data via CSV upload.",                                               "service": "feedback_service"},
    # ── QR & Verification (qr_service + verification_service) ────────────────
    {"key": "qr_generation",          "category": "QR & Verification",    "label": "QR Code Generation",             "description": "Generate PRODUCT, RECEIPT, LOCATION, and SERVICE QR codes with SMS short codes.",               "service": "qr_service"},
    {"key": "product_verification",   "category": "QR & Verification",    "label": "Product Verification",           "description": "AUTHENTIC / ALREADY_USED / UNRECOGNIZED — verify product and service receipt authenticity.",   "service": "verification_service"},
    {"key": "field_agents",           "category": "QR & Verification",    "label": "Field Agent Management",         "description": "Assign and track field agents for fake product investigation and on-site verification.",       "service": "verification_service"},
    # ── Staff service ─────────────────────────────────────────────────────────
    {"key": "staff_verification",     "category": "Staff",                "label": "Staff Identity Verification",    "description": "Public endpoint to verify staff by ORG-NNNNN code. File fraud reports with GPS + photo.",      "service": "staff_service"},
    {"key": "bulk_staff_import",      "category": "Staff",                "label": "Bulk Staff CSV Import",          "description": "Import staff profiles in bulk via CSV upload.",                                               "service": "staff_service"},
    {"key": "staff_analytics",        "category": "Staff",                "label": "Staff Analytics",                "description": "Staff performance analytics: verification counts, fraud reports, feedback scores.",             "service": "staff_service"},
    # ── Queue management (waiting_service) ───────────────────────────────────
    {"key": "waiting_queue",          "category": "Queue Management",     "label": "Multi-Step Queue Management",    "description": "Priority Redis queues, ETA SMS alerts, staff counter sessions, APScheduler reminders.",        "service": "waiting_service"},
    # ── Stakeholder (stakeholder_service) ─────────────────────────────────────
    {"key": "stakeholder_engagement", "category": "Stakeholder",          "label": "Stakeholder Engagement (SEP)",   "description": "Full SEP: stakeholder profiles, stage tracking, activities, communications, Annex 3.",         "service": "stakeholder_service"},
    # ── Translation (translation_service) ────────────────────────────────────
    {"key": "translation",            "category": "Translation",          "label": "Auto-Translation (63 Languages)","description": "NLLB-200 local model. Swahili, English, French, Arabic, and 59 more.",                        "service": "translation_service"},
    {"key": "advanced_translation",   "category": "Translation",          "label": "Advanced Translation",           "description": "Cloud provider fallback chain: Google → DeepL → Microsoft → LibreTranslate.",                "service": "translation_service"},
    # ── Product catalog (product_service) ────────────────────────────────────
    {"key": "product_catalog",        "category": "Product Catalog",      "label": "Product Catalog",                "description": "89 product types, 12 category-attribute tables, MinIO image storage.",                        "service": "product_service"},
    {"key": "product_variations",     "category": "Product Catalog",      "label": "Product Variations",             "description": "Size, colour, weight, and custom attribute variations per product.",                         "service": "product_service"},
    {"key": "rsin",                   "category": "Product Catalog",      "label": "RSIN (Item Numbering)",          "description": "Riviwa Standard Item Number — unique product identity across the platform.",                  "service": "product_service"},
    # ── Integration (integration_service) ────────────────────────────────────
    {"key": "api_access",             "category": "Integration",          "label": "REST API Access",                "description": "Full REST API with API key management. Rate-limited by plan.",                                "service": "integration_service"},
    {"key": "webhooks",               "category": "Integration",          "label": "Webhook Engine",                 "description": "Real-time event delivery to your endpoints with retry and AES-256-GCM payload signing.",       "service": "integration_service"},
    {"key": "oauth2",                 "category": "Integration",          "label": "OAuth2 PKCE",                    "description": "Standard OAuth2 authorization code flow with PKCE for third-party integrations.",             "service": "integration_service"},
    {"key": "widget_embed",           "category": "Integration",          "label": "JavaScript Widget Embed",        "description": "Embed Riviwa feedback widget on any website. Hosted at widget.riviwa.com.",                  "service": "integration_service"},
    {"key": "audit_logs",             "category": "Integration",          "label": "Audit Logs",                     "description": "Immutable audit trail of all API calls, credential accesses, and context sessions.",          "service": "integration_service"},
    # ── Payment processing (payment_service) ──────────────────────────────────
    {"key": "mobile_money",           "category": "Payments",             "label": "Mobile Money (TZ)",              "description": "AzamPay (Airtel/CRDB/NMB), Selcom (Tigo/Halotel), M-Pesa (Vodacom TZ).",                    "service": "payment_service"},
    {"key": "paypal",                 "category": "Payments",             "label": "PayPal",                         "description": "PayPal REST API v2 — Visa, Mastercard, PayPal balance. Ideal for international orgs.",       "service": "payment_service"},
    {"key": "payment_processing",     "category": "Payments",             "label": "Payment Processing (full)",      "description": "Full payment lifecycle: intents, initiation, verification, refunds, webhooks.",               "service": "payment_service"},
    # ── Auth extended (auth_service) ─────────────────────────────────────────
    {"key": "social_login",           "category": "Authentication",       "label": "Social Login",                   "description": "Sign in with Google, Apple ID, and Facebook.",                                             "service": "auth_service"},
    {"key": "id_verification",        "category": "Authentication",       "label": "ID Verification",                "description": "Identity verification via Stripe Identity, Onfido, or Jumio.",                              "service": "auth_service"},
    {"key": "fraud_detection",        "category": "Authentication",       "label": "Fraud Detection",                "description": "Argon2id password hashing + fraud score system with Celery async analysis.",                 "service": "auth_service"},
    {"key": "multi_org",              "category": "Authentication",       "label": "Multi-Org Switching",            "description": "One user account, multiple organisations. Switch context without re-login.",                "service": "auth_service"},
    {"key": "2fa",                    "category": "Authentication",       "label": "Two-Factor Authentication",      "description": "TOTP 2FA (Google Authenticator compatible) for all team members.",                         "service": "auth_service"},
    {"key": "sso",                    "category": "Authentication",       "label": "Single Sign-On (SSO)",           "description": "SAML 2.0 / OIDC SSO with SCIM provisioning.",                                             "service": "auth_service"},
    # ── Platform / enterprise ─────────────────────────────────────────────────
    {"key": "white_label",            "category": "Platform",             "label": "White-Label",                    "description": "Custom domain, branding, and mobile app. Your brand, Riviwa's infrastructure.",              "service": "platform"},
    {"key": "dedicated_support",      "category": "Platform",             "label": "Dedicated Support",              "description": "Priority phone + chat support during business hours. Included from Business plan.",          "service": "platform"},
    {"key": "custom_sla",             "category": "Platform",             "label": "Custom SLA (99.99%)",            "description": "Contractual uptime SLA with financial penalties. Enterprise only.",                         "service": "platform"},
]

# Map feature key → Plan model field name
_KEY_TO_FIELD = {
    "sms_channel": "has_sms_channel", "whatsapp_channel": "has_whatsapp_channel",
    "phone_call_ai": "has_phone_call_ai", "ai_conversation": "has_ai_conversation",
    "ai_insights": "has_ai_insights", "voice_transcription": "has_voice_transcription",
    "ml_predictor": "has_ml_predictor", "spark_streaming": "has_spark_streaming",
    "recommendations": "has_recommendations", "ai_counterfeit": "has_ai_counterfeit",
    "push_notifications": "has_push_notifications", "whatsapp_notif": "has_whatsapp_notif",
    "advanced_analytics": "has_advanced_analytics", "custom_reports": "has_custom_reports",
    "employee_feedback": "has_employee_feedback", "pap_registry": "has_pap_registry",
    "committee_mgmt": "has_committee_mgmt", "bulk_import": "has_bulk_import",
    "qr_generation": "has_qr_generation", "product_verification": "has_product_verification",
    "field_agents": "has_field_agents", "staff_verification": "has_staff_verification",
    "bulk_staff_import": "has_bulk_staff_import", "staff_analytics": "has_staff_analytics",
    "waiting_queue": "has_waiting_queue", "stakeholder_engagement": "has_stakeholder_engagement",
    "translation": "has_translation", "advanced_translation": "has_advanced_translation",
    "product_catalog": "has_product_catalog", "product_variations": "has_product_variations",
    "rsin": "has_rsin", "api_access": "has_api_access", "webhooks": "has_webhooks",
    "oauth2": "has_oauth2", "widget_embed": "has_widget_embed", "audit_logs": "has_audit_logs",
    "mobile_money": "has_mobile_money", "paypal": "has_paypal",
    "payment_processing": "has_payment_processing",
    "social_login": "has_social_login", "id_verification": "has_id_verification",
    "fraud_detection": "has_fraud_detection", "multi_org": "has_multi_org",
    "2fa": "has_2fa", "sso": "has_sso", "white_label": "has_white_label",
    "dedicated_support": "has_dedicated_support", "custom_sla": "has_custom_sla",
}


# ── Serialisers ───────────────────────────────────────────────────────────────

def _plan_out(p: Plan, include_admin: bool = False) -> dict:
    features = {}
    for feat in FEATURE_CATALOG:
        field = _KEY_TO_FIELD.get(feat["key"], f"has_{feat['key']}")
        features[feat["key"]] = getattr(p, field, False)

    out = {
        "id":           str(p.id),
        "slug":         p.slug,
        "display_name": p.display_name,
        "tagline":      p.tagline,
        "description":  p.description,
        "pricing": {
            "monthly_usd":       str(p.monthly_price_usd),
            "annual_usd":        str(p.annual_price_usd),
            "annual_monthly_usd": str(p.annual_price_usd),
            "annual_total_usd":  str(p.annual_price_usd * 12),
            "annual_savings_pct": 20,
            "is_custom":         p.is_custom,
        },
        "trial_days": p.trial_days,
        "limits": {
            "team_members":          p.max_team_members,
            "projects":              p.max_projects,
            "submissions_per_month": p.max_submissions_per_month,
            "sms_per_month":         p.max_sms_per_month,
            "api_calls_per_month":   p.max_api_calls_per_month,
            "storage_gb":            p.max_storage_gb,
            "qr_per_month":          p.max_qr_per_month,
            "staff_profiles":        p.max_staff_profiles,
        },
        "features":    features,
        "sla":         p.uptime_sla,
        "sort_order":  p.sort_order,
    }
    if include_admin:
        out["is_active"] = p.is_active
        out["is_public"] = p.is_public
        out["created_at"] = p.created_at.isoformat()
        out["updated_at"] = p.updated_at.isoformat()
    return out


def _addon_out(a: AddOn) -> dict:
    return {
        "id": str(a.id), "slug": a.slug, "name": a.name,
        "description": a.description, "type": a.type,
        "price_usd": str(a.price_usd), "unit": a.unit,
        "unit_quantity": a.unit_quantity, "is_active": a.is_active,
        "created_at": a.created_at.isoformat(),
    }


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("", summary="List all public plans")
async def list_plans(db: DbDep) -> dict:
    svc   = SubscriptionService(db)
    plans = await svc.list_plans()
    return {"plans": [_plan_out(p) for p in plans]}


@router.get("/compare", summary="Side-by-side plan comparison")
async def compare_plans(db: DbDep) -> dict:
    """Returns all plans with every feature listed — ideal for pricing page rendering."""
    svc   = SubscriptionService(db)
    plans = await svc.list_plans()

    # Build comparison matrix
    comparison = []
    for feat in FEATURE_CATALOG:
        field = _KEY_TO_FIELD.get(feat["key"], f"has_{feat['key']}")
        row = {
            "key":         feat["key"],
            "category":    feat["category"],
            "label":       feat["label"],
            "description": feat["description"],
            "service":     feat["service"],
            "plans": {
                p.slug: getattr(p, field, False)
                for p in plans
            },
        }
        comparison.append(row)

    # Group by category
    from collections import defaultdict
    grouped: dict = defaultdict(list)
    for row in comparison:
        grouped[row["category"]].append(row)

    return {
        "plans":      [_plan_out(p) for p in plans],
        "comparison": dict(grouped),
        "categories": list(grouped.keys()),
    }


@router.get("/features", summary="Catalog of all features available in Riviwa")
async def list_features(
    category: Optional[str] = Query(default=None, description="Filter by category"),
    service:  Optional[str] = Query(default=None, description="Filter by service"),
) -> dict:
    """Returns every feature in the Riviwa platform with descriptions and service attribution."""
    feats = FEATURE_CATALOG
    if category:
        feats = [f for f in feats if f["category"].lower() == category.lower()]
    if service:
        feats = [f for f in feats if f["service"].lower() == service.lower()]

    # Group by category
    from collections import defaultdict
    grouped: dict = defaultdict(list)
    for f in feats:
        grouped[f["category"]].append(f)

    categories = sorted(set(f["category"] for f in FEATURE_CATALOG))
    services   = sorted(set(f["service"]  for f in FEATURE_CATALOG))

    return {
        "total_features":  len(FEATURE_CATALOG),
        "categories":      categories,
        "services":        services,
        "features":        list(feats),
        "grouped":         dict(grouped),
    }


@router.get("/addons", summary="List available add-ons")
async def list_addons(db: DbDep) -> dict:
    result = await db.execute(select(AddOn).where(AddOn.is_active == True).order_by(AddOn.name))
    return {"addons": [_addon_out(a) for a in result.scalars().all()]}


@router.get("/{plan_id_or_slug}", summary="Get plan detail with full feature list")
async def get_plan(plan_id_or_slug: str, db: DbDep) -> dict:
    svc = SubscriptionService(db)
    try:
        uuid.UUID(plan_id_or_slug)
        plan = await svc.get_plan(plan_id_or_slug)
    except ValueError:
        plan = await svc.get_plan_by_slug(plan_id_or_slug)
    return _plan_out(plan)


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN — PLAN MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/admin/plans", summary="Admin: list all plans including inactive")
async def admin_list_plans(db: DbDep, _: AdminDep) -> dict:
    result = await db.execute(select(Plan).order_by(Plan.sort_order))
    plans  = list(result.scalars().all())
    return {
        "total": len(plans),
        "plans": [_plan_out(p, include_admin=True) for p in plans],
    }


@router.post("/admin/plans", summary="Admin: create a new plan", status_code=201)
async def admin_create_plan(body: dict, db: DbDep, _: AdminDep) -> dict:
    """
    Create a new subscription plan. Pass any combination of pricing, limits, and features.

    Required: slug, display_name, monthly_price_usd, annual_price_usd
    All feature flags default to False unless specified.
    All limit fields default to 0 unless specified (-1 = unlimited).
    """
    if not body.get("slug"):
        raise ValidationError("slug is required.")
    if not body.get("display_name"):
        raise ValidationError("display_name is required.")

    existing = (await db.execute(select(Plan).where(Plan.slug == body["slug"]))).scalar_one_or_none()
    if existing:
        raise ConflictError(f"Plan with slug '{body['slug']}' already exists.")

    valid = {k: v for k, v in body.items() if hasattr(Plan, k) and k not in ("id", "created_at", "updated_at")}
    plan  = Plan(**valid)
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return _plan_out(plan, include_admin=True)


@router.patch("/admin/plans/{plan_id}", summary="Admin: update any plan field")
async def admin_update_plan(plan_id: str, body: dict, db: DbDep, _: AdminDep) -> dict:
    """Update any combination of plan fields in a single call."""
    plan = await db.get(Plan, uuid.UUID(plan_id))
    if not plan:
        raise NotFoundError("Plan")
    immutable = {"id", "slug", "created_at"}
    for k, v in body.items():
        if hasattr(plan, k) and k not in immutable:
            setattr(plan, k, v)
    plan.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(plan)
    return _plan_out(plan, include_admin=True)


@router.patch("/admin/plans/{plan_id}/pricing", summary="Admin: update plan pricing")
async def admin_update_pricing(plan_id: str, body: dict, db: DbDep, _: AdminDep) -> dict:
    """
    Update pricing for a plan without touching features or limits.

    Body:
    {
      "monthly_price_usd": "49.00",
      "annual_price_usd":  "39.00",
      "is_custom":         false,
      "trial_days":        14
    }
    """
    plan = await db.get(Plan, uuid.UUID(plan_id))
    if not plan:
        raise NotFoundError("Plan")

    pricing_fields = {"monthly_price_usd", "annual_price_usd", "is_custom", "trial_days", "uptime_sla"}
    for k, v in body.items():
        if k in pricing_fields:
            setattr(plan, k, Decimal(str(v)) if "price" in k else v)
    plan.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(plan)
    return {
        "id":    str(plan.id),
        "slug":  plan.slug,
        "pricing": {
            "monthly_usd":       str(plan.monthly_price_usd),
            "annual_usd":        str(plan.annual_price_usd),
            "annual_total_usd":  str(plan.annual_price_usd * 12),
            "is_custom":         plan.is_custom,
            "trial_days":        plan.trial_days,
            "uptime_sla":        plan.uptime_sla,
        },
        "updated_at": plan.updated_at.isoformat(),
    }


@router.patch("/admin/plans/{plan_id}/limits", summary="Admin: update plan usage limits")
async def admin_update_limits(plan_id: str, body: dict, db: DbDep, _: AdminDep) -> dict:
    """
    Update usage limits for a plan. Use -1 for unlimited.

    Body:
    {
      "max_team_members":          25,
      "max_projects":              15,
      "max_submissions_per_month": 5000,
      "max_sms_per_month":         2000,
      "max_api_calls_per_month":   10000,
      "max_storage_gb":            25,
      "max_qr_per_month":          500,
      "max_staff_profiles":        100
    }
    """
    plan = await db.get(Plan, uuid.UUID(plan_id))
    if not plan:
        raise NotFoundError("Plan")

    limit_fields = {
        "max_team_members", "max_projects", "max_submissions_per_month",
        "max_sms_per_month", "max_api_calls_per_month", "max_storage_gb",
        "max_qr_per_month", "max_staff_profiles",
    }
    for k, v in body.items():
        if k in limit_fields:
            setattr(plan, k, int(v))
    plan.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(plan)
    return {"id": str(plan.id), "slug": plan.slug, "limits": {
        "team_members":          plan.max_team_members,
        "projects":              plan.max_projects,
        "submissions_per_month": plan.max_submissions_per_month,
        "sms_per_month":         plan.max_sms_per_month,
        "api_calls_per_month":   plan.max_api_calls_per_month,
        "storage_gb":            plan.max_storage_gb,
        "qr_per_month":          plan.max_qr_per_month,
        "staff_profiles":        plan.max_staff_profiles,
    }, "updated_at": plan.updated_at.isoformat()}


@router.patch("/admin/plans/{plan_id}/features", summary="Admin: toggle features on/off for a plan")
async def admin_update_features(plan_id: str, body: dict, db: DbDep, _: AdminDep) -> dict:
    """
    Enable or disable any set of features on a plan.

    Body: { "feature_key": true/false, ... }
    Example: { "ai_conversation": true, "phone_call_ai": false, "webhooks": true }

    All available feature keys: GET /api/v1/plans/features
    """
    plan = await db.get(Plan, uuid.UUID(plan_id))
    if not plan:
        raise NotFoundError("Plan")

    unknown_keys = []
    changed = {}
    for key, enabled in body.items():
        field = _KEY_TO_FIELD.get(key)
        if not field:
            unknown_keys.append(key)
            continue
        if not hasattr(plan, field):
            unknown_keys.append(key)
            continue
        setattr(plan, field, bool(enabled))
        changed[key] = bool(enabled)

    plan.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(plan)

    result = {"id": str(plan.id), "slug": plan.slug, "features_changed": changed}
    if unknown_keys:
        result["warnings"] = [f"Unknown feature key(s): {unknown_keys}. See GET /api/v1/plans/features for valid keys."]
    result["features"] = {
        feat["key"]: getattr(plan, _KEY_TO_FIELD.get(feat["key"], f"has_{feat['key']}"), False)
        for feat in FEATURE_CATALOG
    }
    return result


@router.post("/admin/plans/{plan_id}/duplicate", summary="Admin: clone a plan")
async def admin_duplicate_plan(plan_id: str, body: dict, db: DbDep, _: AdminDep) -> dict:
    """
    Clone an existing plan with a new slug and optionally new name/pricing.

    Body:
    {
      "slug":         "business-ngo",
      "display_name": "Business NGO",
      "monthly_price_usd": "249.00",   # optional overrides
      "annual_price_usd":  "199.00"
    }
    """
    source = await db.get(Plan, uuid.UUID(plan_id))
    if not source:
        raise NotFoundError("Plan")

    new_slug = body.get("slug")
    if not new_slug:
        raise ValidationError("slug is required for duplicate.")
    exists = (await db.execute(select(Plan).where(Plan.slug == new_slug))).scalar_one_or_none()
    if exists:
        raise ConflictError(f"Plan slug '{new_slug}' already exists.")

    # Copy all fields from source
    new_plan = Plan(
        **{
            col: getattr(source, col)
            for col in source.__class__.__table__.columns.keys()
            if col not in ("id", "created_at", "updated_at")
        }
    )
    # Apply overrides
    for k, v in body.items():
        if hasattr(new_plan, k) and k not in ("id", "created_at", "updated_at"):
            setattr(new_plan, k, v)
    new_plan.id         = uuid.uuid4()
    new_plan.is_active  = False   # starts inactive — admin reviews before publishing
    new_plan.is_public  = False
    new_plan.created_at = datetime.utcnow()
    new_plan.updated_at = datetime.utcnow()

    db.add(new_plan)
    await db.commit()
    await db.refresh(new_plan)
    return _plan_out(new_plan, include_admin=True)


@router.delete("/admin/plans/{plan_id}", summary="Admin: deactivate a plan (soft delete)")
async def admin_deactivate_plan(plan_id: str, db: DbDep, _: AdminDep) -> dict:
    """
    Deactivates a plan — hides it from public listing.
    Does NOT delete it or affect existing subscribers.
    """
    plan = await db.get(Plan, uuid.UUID(plan_id))
    if not plan:
        raise NotFoundError("Plan")
    if plan.slug in ("starter", "professional", "business", "enterprise"):
        raise ValidationError("Default plans cannot be deactivated. Create a custom plan instead.")
    plan.is_active  = False
    plan.is_public  = False
    plan.updated_at = datetime.utcnow()
    await db.commit()
    return {"message": f"Plan '{plan.display_name}' deactivated.", "id": str(plan.id)}


@router.patch("/admin/plans/{plan_id}/publish", summary="Admin: publish or unpublish a plan")
async def admin_publish_plan(plan_id: str, body: dict, db: DbDep, _: AdminDep) -> dict:
    plan = await db.get(Plan, uuid.UUID(plan_id))
    if not plan:
        raise NotFoundError("Plan")
    plan.is_public  = body.get("is_public", True)
    plan.is_active  = body.get("is_active", True)
    plan.updated_at = datetime.utcnow()
    await db.commit()
    return {"message": f"Plan '{plan.display_name}' {'published' if plan.is_public else 'unpublished'}.",
            "is_public": plan.is_public, "is_active": plan.is_active}


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN — ADD-ON MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/admin/addons", summary="Admin: list all add-ons including inactive")
async def admin_list_addons(db: DbDep, _: AdminDep) -> dict:
    result = await db.execute(select(AddOn).order_by(AddOn.name))
    return {"addons": [_addon_out(a) for a in result.scalars().all()]}


@router.post("/admin/addons", summary="Admin: create a new add-on", status_code=201)
async def admin_create_addon(body: dict, db: DbDep, _: AdminDep) -> dict:
    """
    Create a new purchasable add-on.

    Required: slug, name, type, price_usd
    Optional: description, unit, unit_quantity
    """
    if not body.get("slug"):
        raise ValidationError("slug is required.")
    exists = (await db.execute(select(AddOn).where(AddOn.slug == body["slug"]))).scalar_one_or_none()
    if exists:
        raise ConflictError(f"Add-on slug '{body['slug']}' already exists.")

    addon = AddOn(
        slug          = body["slug"],
        name          = body["name"],
        description   = body.get("description", ""),
        type          = body["type"],
        price_usd     = Decimal(str(body["price_usd"])),
        unit          = body.get("unit", ""),
        unit_quantity = body.get("unit_quantity", 1),
        is_active     = body.get("is_active", True),
    )
    db.add(addon)
    await db.commit()
    await db.refresh(addon)
    return _addon_out(addon)


@router.patch("/admin/addons/{addon_id}", summary="Admin: update an add-on")
async def admin_update_addon(addon_id: str, body: dict, db: DbDep, _: AdminDep) -> dict:
    addon = await db.get(AddOn, uuid.UUID(addon_id))
    if not addon:
        raise NotFoundError("Add-on")
    immutable = {"id", "slug", "created_at"}
    for k, v in body.items():
        if hasattr(addon, k) and k not in immutable:
            setattr(addon, k, Decimal(str(v)) if k == "price_usd" else v)
    await db.commit()
    await db.refresh(addon)
    return _addon_out(addon)


@router.delete("/admin/addons/{addon_id}", summary="Admin: deactivate an add-on")
async def admin_deactivate_addon(addon_id: str, db: DbDep, _: AdminDep) -> dict:
    addon = await db.get(AddOn, uuid.UUID(addon_id))
    if not addon:
        raise NotFoundError("Add-on")
    addon.is_active = False
    await db.commit()
    return {"message": f"Add-on '{addon.name}' deactivated.", "id": str(addon.id)}

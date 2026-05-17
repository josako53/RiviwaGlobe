"""db/seed.py — Seed all Riviwa plans, add-ons, promo codes, and sale campaigns."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from models.subscription import AddOn, Plan, PromoCode, Sale

log = structlog.get_logger(__name__)

# ── Feature flag sets per plan ────────────────────────────────────────────────

_STARTER_FEATURES = dict(
    has_2fa=False,
    has_sso=False,
    has_white_label=False,
    has_dedicated_support=False,
    has_custom_sla=False,
    has_employee_feedback=False,
    has_pap_registry=False,
    has_committee_mgmt=False,
    has_bulk_import=False,
    has_sms_channel=False,
    has_whatsapp_channel=False,
    has_phone_call_ai=False,
    has_ai_conversation=False,
    has_ai_insights=False,
    has_voice_transcription=False,
    has_push_notifications=False,
    has_whatsapp_notif=False,
    has_advanced_analytics=False,
    has_custom_reports=False,
    has_spark_streaming=False,
    has_ml_predictor=False,
    has_qr_generation=False,
    has_product_verification=False,
    has_ai_counterfeit=False,
    has_field_agents=False,
    has_staff_verification=False,
    has_bulk_staff_import=False,
    has_staff_analytics=False,
    has_queue_management=False,
    has_stakeholder_engagement=False,
    has_translation=False,
    has_advanced_translation=False,
    has_api_access=False,
    has_webhooks=False,
    has_oauth2=False,
    has_widget_embed=False,
    has_audit_logs=False,
    has_payment_processing=False,
    has_paypal=False,
    has_mobile_money=False,
    has_product_catalog=False,
    has_product_variations=False,
    has_rsin=False,
    has_recommendations=False,
    has_geo_proximity=False,
    has_waiting_queue=False,
    has_id_verification=False,
    has_fraud_detection=False,
    has_social_login=False,
    has_multi_org=False,
)

_PROFESSIONAL_FEATURES = dict(
    has_2fa=True,
    has_sso=False,
    has_white_label=False,
    has_dedicated_support=False,
    has_custom_sla=False,
    has_employee_feedback=True,
    has_pap_registry=True,
    has_committee_mgmt=False,
    has_bulk_import=False,
    has_sms_channel=True,
    has_whatsapp_channel=True,
    has_phone_call_ai=False,
    has_ai_conversation=True,
    has_ai_insights=False,
    has_voice_transcription=True,
    has_push_notifications=True,
    has_whatsapp_notif=True,
    has_advanced_analytics=True,
    has_custom_reports=False,
    has_spark_streaming=False,
    has_ml_predictor=False,
    has_qr_generation=True,
    has_product_verification=True,
    has_ai_counterfeit=False,
    has_field_agents=False,
    has_staff_verification=True,
    has_bulk_staff_import=False,
    has_staff_analytics=False,
    has_queue_management=False,
    has_stakeholder_engagement=False,
    has_translation=True,
    has_advanced_translation=False,
    has_api_access=True,
    has_webhooks=False,
    has_oauth2=True,
    has_widget_embed=True,
    has_audit_logs=False,
    has_payment_processing=False,
    has_paypal=False,
    has_mobile_money=False,
    has_product_catalog=True,
    has_product_variations=False,
    has_rsin=False,
    has_recommendations=True,
    has_geo_proximity=False,
    has_waiting_queue=False,
    has_id_verification=False,
    has_fraud_detection=True,
    has_social_login=True,
    has_multi_org=True,
)

_BUSINESS_FEATURES = dict(
    has_2fa=True,
    has_sso=False,
    has_white_label=False,
    has_dedicated_support=True,
    has_custom_sla=False,
    has_employee_feedback=True,
    has_pap_registry=True,
    has_committee_mgmt=True,
    has_bulk_import=True,
    has_sms_channel=True,
    has_whatsapp_channel=True,
    has_phone_call_ai=True,
    has_ai_conversation=True,
    has_ai_insights=True,
    has_voice_transcription=True,
    has_push_notifications=True,
    has_whatsapp_notif=True,
    has_advanced_analytics=True,
    has_custom_reports=True,
    has_spark_streaming=True,
    has_ml_predictor=True,
    has_qr_generation=True,
    has_product_verification=True,
    has_ai_counterfeit=True,
    has_field_agents=True,
    has_staff_verification=True,
    has_bulk_staff_import=True,
    has_staff_analytics=True,
    has_queue_management=True,
    has_stakeholder_engagement=True,
    has_translation=True,
    has_advanced_translation=True,
    has_api_access=True,
    has_webhooks=True,
    has_oauth2=True,
    has_widget_embed=True,
    has_audit_logs=True,
    has_payment_processing=True,
    has_paypal=True,
    has_mobile_money=True,
    has_product_catalog=True,
    has_product_variations=True,
    has_rsin=True,
    has_recommendations=True,
    has_geo_proximity=True,
    has_waiting_queue=True,
    has_id_verification=True,
    has_fraud_detection=True,
    has_social_login=True,
    has_multi_org=True,
)

_ENTERPRISE_FEATURES = {k: True for k in _BUSINESS_FEATURES}
_ENTERPRISE_FEATURES["has_sso"]         = True
_ENTERPRISE_FEATURES["has_white_label"] = True
_ENTERPRISE_FEATURES["has_custom_sla"]  = True


# ── Plan definitions ──────────────────────────────────────────────────────────

PLANS = [
    {
        "slug": "starter",
        "display_name": "Starter",
        "tagline": "Everything you need to start collecting feedback",
        "description": (
            "Perfect for small NGOs, community-based organisations, and local government units. "
            "Web and mobile feedback collection with email notifications and basic analytics."
        ),
        "monthly_price_usd": Decimal("49.00"),
        "annual_price_usd":  Decimal("39.00"),
        "trial_days": 14,
        "sort_order": 1,
        "max_team_members": 5,
        "max_projects": 3,
        "max_submissions_per_month": 500,
        "max_sms_per_month": 200,
        "max_api_calls_per_month": 0,
        "max_storage_gb": 5,
        "max_qr_per_month": 0,
        "max_staff_profiles": 0,
        "uptime_sla": "99.5%",
        **_STARTER_FEATURES,
    },
    {
        "slug": "professional",
        "display_name": "Professional",
        "tagline": "AI-powered GRM for growing organisations",
        "description": (
            "Ideal for hospitals, universities, utilities, and mid-size banks. "
            "Includes AI conversation, SMS/WhatsApp channels, QR verification, "
            "advanced analytics, translation, API access, and social login."
        ),
        "monthly_price_usd": Decimal("149.00"),
        "annual_price_usd":  Decimal("119.00"),
        "trial_days": 14,
        "sort_order": 2,
        "max_team_members": 25,
        "max_projects": 15,
        "max_submissions_per_month": 5000,
        "max_sms_per_month": 2000,
        "max_api_calls_per_month": 10000,
        "max_storage_gb": 25,
        "max_qr_per_month": 500,
        "max_staff_profiles": 100,
        "uptime_sla": "99.9%",
        **_PROFESSIONAL_FEATURES,
    },
    {
        "slug": "business",
        "display_name": "Business",
        "tagline": "Full-stack GRM for enterprises and governments",
        "description": (
            "Built for commercial banks, government ministries, large hospitals, and international NGOs. "
            "All 15 Riviwa services: AI phone IVR, Spark analytics, ML predictor, stakeholder SEP, "
            "product catalog with RSIN, waiting queue, PayPal + mobile money payments, "
            "field agents, staff verification, 63-language translation, webhook engine, audit logs."
        ),
        "monthly_price_usd": Decimal("399.00"),
        "annual_price_usd":  Decimal("319.00"),
        "trial_days": 14,
        "sort_order": 3,
        "max_team_members": 100,
        "max_projects": -1,
        "max_submissions_per_month": -1,
        "max_sms_per_month": 10000,
        "max_api_calls_per_month": 100000,
        "max_storage_gb": 100,
        "max_qr_per_month": -1,
        "max_staff_profiles": -1,
        "uptime_sla": "99.95%",
        **_BUSINESS_FEATURES,
    },
    {
        "slug": "enterprise",
        "display_name": "Enterprise",
        "tagline": "Unlimited power. Dedicated support. Custom everything.",
        "description": (
            "For World Bank, UN agencies, governments, multinationals, and donor programmes. "
            "Everything in Business plus: unlimited team/projects/submissions, SSO, white-label, "
            "custom SLA (99.99%), on-premise option, dedicated CSM, custom AI fine-tuning, "
            "SCIM, HIPAA-ready, volume SMS pricing negotiated with carriers."
        ),
        "monthly_price_usd": Decimal("0"),
        "annual_price_usd":  Decimal("0"),
        "trial_days": 30,
        "sort_order": 4,
        "is_custom": True,
        "max_team_members": -1,
        "max_projects": -1,
        "max_submissions_per_month": -1,
        "max_sms_per_month": -1,
        "max_api_calls_per_month": -1,
        "max_storage_gb": -1,
        "max_qr_per_month": -1,
        "max_staff_profiles": -1,
        "uptime_sla": "99.99%",
        **_ENTERPRISE_FEATURES,
    },
]


ADDONS = [
    {"slug": "extra-sms-1k",     "name": "Extra SMS Bundle",         "description": "1,000 additional SMS notifications or AI conversations",                      "type": "extra_sms",           "price_usd": Decimal("10.00"),  "unit": "1,000 SMS",    "unit_quantity": 1000},
    {"slug": "extra-users-5",    "name": "Extra Team Members (5)",   "description": "5 additional team member seats beyond plan limit",                            "type": "extra_users",          "price_usd": Decimal("25.00"),  "unit": "5 users",      "unit_quantity": 5},
    {"slug": "extra-storage-10g","name": "Extra Storage (10 GB)",    "description": "10 GB additional file and voice recording storage",                           "type": "extra_storage",        "price_usd": Decimal("5.00"),   "unit": "10 GB",        "unit_quantity": 10},
    {"slug": "extra-api-10k",    "name": "Extra API Calls",          "description": "10,000 additional API calls per month",                                       "type": "extra_api_calls",      "price_usd": Decimal("5.00"),   "unit": "10,000 calls", "unit_quantity": 10000},
    {"slug": "extra-qr-500",     "name": "Extra QR Codes (500)",     "description": "500 additional QR codes generated per month",                                 "type": "extra_qr",             "price_usd": Decimal("5.00"),   "unit": "500 QR",       "unit_quantity": 500},
    {"slug": "whatsapp-biz",     "name": "WhatsApp Business API",    "description": "Meta-verified WhatsApp Business sender — required for high-volume WhatsApp",  "type": "whatsapp_business",    "price_usd": Decimal("25.00"),  "unit": "month",        "unit_quantity": 1},
    {"slug": "custom-ai",        "name": "Custom AI Model",          "description": "Fine-tune Riviwa AI on your organisation's own data and terminology",         "type": "custom_ai",            "price_usd": Decimal("199.00"), "unit": "month",        "unit_quantity": 1},
    {"slug": "dedicated-kafka",  "name": "Dedicated Kafka Cluster",  "description": "Isolated event streaming cluster — for compliance or high-throughput needs",  "type": "dedicated_kafka",      "price_usd": Decimal("99.00"),  "unit": "month",        "unit_quantity": 1},
    {"slug": "advanced-trans",   "name": "Advanced Translation",     "description": "Cloud provider fallback (Google, DeepL, Microsoft) for all 63 languages",     "type": "advanced_translation", "price_usd": Decimal("15.00"),  "unit": "month",        "unit_quantity": 1},
    {"slug": "phone-ai-minutes", "name": "Phone Call AI (per min)",  "description": "Twilio IVR AI voice minutes — billed on actual usage",                        "type": "phone_call_ai",        "price_usd": Decimal("0.05"),   "unit": "minute",       "unit_quantity": 1},
    {"slug": "extra-project",    "name": "Extra Project",            "description": "One additional project slot beyond plan limit",                                "type": "extra_users",          "price_usd": Decimal("10.00"),  "unit": "project",      "unit_quantity": 1},
]


# ── Promo code definitions ────────────────────────────────────────────────────
# All dates are UTC.

PROMO_CODES = [
    {
        "code": "LAUNCH2026",
        "name": "Riviwa Launch Offer",
        "description": "30% off your first 3 months — available to all new subscribers during our 2026 launch.",
        "discount_type": "percentage",
        "discount_value": Decimal("30"),
        "duration": "repeating",
        "duration_months": 3,
        "max_redemptions": -1,
        "eligible_plans": None,   # all plans
        "new_subscribers_only": True,
        "min_plan_price_usd": Decimal("0"),
        "expires_at": datetime(2026, 12, 31, 23, 59, 59),
        "is_active": True,
    },
    {
        "code": "ANNUAL20",
        "name": "Annual Plan Discount",
        "description": "Extra 20% off when you commit to an annual plan. Applies to the first year.",
        "discount_type": "percentage",
        "discount_value": Decimal("20"),
        "duration": "once",
        "duration_months": 1,
        "max_redemptions": -1,
        "eligible_plans": None,
        "new_subscribers_only": False,
        "min_plan_price_usd": Decimal("0"),
        "expires_at": None,
        "is_active": True,
    },
    {
        "code": "NGO50",
        "name": "NGO & Nonprofit 50% Discount",
        "description": "50% off the Starter plan forever — for registered NGOs, CBOs, and nonprofits. Limited to 100 organisations.",
        "discount_type": "percentage",
        "discount_value": Decimal("50"),
        "duration": "forever",
        "duration_months": 0,
        "max_redemptions": 100,
        "eligible_plans": ["starter"],
        "new_subscribers_only": True,
        "min_plan_price_usd": Decimal("0"),
        "expires_at": None,
        "is_active": True,
    },
    {
        "code": "PARTNER25",
        "name": "Partner Referral — 25% off",
        "description": "Referred by a Riviwa partner? Get 25% off for your first 6 months on Professional or Business.",
        "discount_type": "percentage",
        "discount_value": Decimal("25"),
        "duration": "repeating",
        "duration_months": 6,
        "max_redemptions": 500,
        "eligible_plans": ["professional", "business"],
        "new_subscribers_only": True,
        "min_plan_price_usd": Decimal("0"),
        "expires_at": datetime(2026, 12, 31, 23, 59, 59),
        "is_active": True,
    },
    {
        "code": "WELCOME1",
        "name": "Welcome — 1 Free Month",
        "description": "Start with one free month on any paid plan. No credit card required during trial.",
        "discount_type": "free_months",
        "discount_value": Decimal("1"),
        "duration": "once",
        "duration_months": 1,
        "max_redemptions": -1,
        "eligible_plans": None,
        "new_subscribers_only": True,
        "min_plan_price_usd": Decimal("0"),
        "expires_at": datetime(2026, 9, 30, 23, 59, 59),
        "is_active": True,
    },
    {
        "code": "GOV30",
        "name": "Government Institution Discount",
        "description": "30% off forever for verified government ministries, agencies, and public hospitals.",
        "discount_type": "percentage",
        "discount_value": Decimal("30"),
        "duration": "forever",
        "duration_months": 0,
        "max_redemptions": 200,
        "eligible_plans": ["professional", "business", "enterprise"],
        "new_subscribers_only": False,
        "min_plan_price_usd": Decimal("149"),
        "expires_at": None,
        "is_active": True,
    },
    {
        "code": "UPGRADE30",
        "name": "Business Upgrade Discount",
        "description": "30% off your first month when upgrading to the Business plan.",
        "discount_type": "percentage",
        "discount_value": Decimal("30"),
        "duration": "once",
        "duration_months": 1,
        "max_redemptions": -1,
        "eligible_plans": ["business"],
        "new_subscribers_only": False,
        "min_plan_price_usd": Decimal("0"),
        "expires_at": datetime(2026, 12, 31, 23, 59, 59),
        "is_active": True,
    },
    {
        "code": "STUDENT15",
        "name": "Student & University Discount",
        "description": "15% off Professional for university research projects and student-run organisations.",
        "discount_type": "percentage",
        "discount_value": Decimal("15"),
        "duration": "repeating",
        "duration_months": 12,
        "max_redemptions": 300,
        "eligible_plans": ["professional"],
        "new_subscribers_only": True,
        "min_plan_price_usd": Decimal("0"),
        "expires_at": datetime(2027, 6, 30, 23, 59, 59),
        "is_active": True,
    },
    {
        "code": "EARLYBIRD40",
        "name": "Early Bird — 40% off",
        "description": "40% off first 2 months for organisations that subscribed before August 2026.",
        "discount_type": "percentage",
        "discount_value": Decimal("40"),
        "duration": "repeating",
        "duration_months": 2,
        "max_redemptions": 50,
        "eligible_plans": None,
        "new_subscribers_only": True,
        "min_plan_price_usd": Decimal("0"),
        "expires_at": datetime(2026, 8, 1, 0, 0, 0),
        "is_active": True,
    },
    {
        "code": "DONOR10",
        "name": "Donor-Funded Programme Discount",
        "description": "$10 off per month for organisations operating donor-funded GRM programmes (e.g., World Bank, USAID).",
        "discount_type": "fixed_amount",
        "discount_value": Decimal("10"),
        "duration": "forever",
        "duration_months": 0,
        "max_redemptions": -1,
        "eligible_plans": ["professional", "business"],
        "new_subscribers_only": False,
        "min_plan_price_usd": Decimal("149"),
        "expires_at": None,
        "is_active": True,
    },
]


# ── Sale campaign definitions ─────────────────────────────────────────────────

SALES = [
    {
        "name": "Launch Week Sale",
        "description": (
            "Riviwa's official launch — 40% off all plans for new subscribers. "
            "Auto-applied at checkout, no code needed."
        ),
        "banner_text": "Launch Week — 40% OFF for new subscribers. Ends 31 May!",
        "start_at": datetime(2026, 5, 17, 0, 0, 0),
        "end_at":   datetime(2026, 5, 31, 23, 59, 59),
        "discount_type":  "percentage",
        "discount_value": Decimal("40"),
        "duration":       "once",
        "duration_months": 1,
        "eligible_plans":          None,    # all plans
        "eligible_billing_cycles": None,    # monthly and annual
        "new_subscribers_only":    True,
        "max_redemptions": -1,
        "auto_apply": True,
        "is_active": True,
    },
    {
        "name": "Mid-Year Sale 2026",
        "description": (
            "Celebrating Riviwa's first quarter — 25% off all plans for the entire month of June."
        ),
        "banner_text": "Mid-Year Sale — 25% OFF all plans. June only!",
        "start_at": datetime(2026, 6, 1, 0, 0, 0),
        "end_at":   datetime(2026, 6, 30, 23, 59, 59),
        "discount_type":  "percentage",
        "discount_value": Decimal("25"),
        "duration":       "once",
        "duration_months": 1,
        "eligible_plans":          None,
        "eligible_billing_cycles": None,
        "new_subscribers_only":    False,
        "max_redemptions": -1,
        "auto_apply": True,
        "is_active": True,
    },
    {
        "name": "Annual Plan Bonus — July & August",
        "description": (
            "Switch to annual billing in July or August and get an extra 15% off. "
            "Stacks with your existing plan pricing."
        ),
        "banner_text": "Go Annual — extra 15% off. July & August only!",
        "start_at": datetime(2026, 7, 1, 0, 0, 0),
        "end_at":   datetime(2026, 8, 31, 23, 59, 59),
        "discount_type":  "percentage",
        "discount_value": Decimal("15"),
        "duration":       "once",
        "duration_months": 1,
        "eligible_plans":          None,
        "eligible_billing_cycles": ["annual"],
        "new_subscribers_only":    False,
        "max_redemptions": -1,
        "auto_apply": True,
        "is_active": True,
    },
    {
        "name": "Black Friday 2026",
        "description": (
            "Biggest Riviwa discount of the year — 50% off all plans. "
            "One day only, auto-applied at checkout."
        ),
        "banner_text": "Black Friday — 50% OFF everything. Today only!",
        "start_at": datetime(2026, 11, 27, 0, 0, 0),
        "end_at":   datetime(2026, 11, 27, 23, 59, 59),
        "discount_type":  "percentage",
        "discount_value": Decimal("50"),
        "duration":       "once",
        "duration_months": 1,
        "eligible_plans":          None,
        "eligible_billing_cycles": None,
        "new_subscribers_only":    False,
        "max_redemptions": 1000,
        "auto_apply": True,
        "is_active": True,
    },
    {
        "name": "Cyber Monday 2026",
        "description": "Follow-up to Black Friday — 35% off Professional and Business for Cyber Monday.",
        "banner_text": "Cyber Monday — 35% OFF Pro & Business. Ends midnight!",
        "start_at": datetime(2026, 11, 30, 0, 0, 0),
        "end_at":   datetime(2026, 11, 30, 23, 59, 59),
        "discount_type":  "percentage",
        "discount_value": Decimal("35"),
        "duration":       "once",
        "duration_months": 1,
        "eligible_plans":          ["professional", "business"],
        "eligible_billing_cycles": None,
        "new_subscribers_only":    False,
        "max_redemptions": 500,
        "auto_apply": True,
        "is_active": True,
    },
    {
        "name": "New Year 2027 Kickstart",
        "description": "Start 2027 strong — 20% off all plans for the first 2 weeks of January.",
        "banner_text": "New Year 2027 — 20% OFF all plans. 1–14 January!",
        "start_at": datetime(2027, 1, 1, 0, 0, 0),
        "end_at":   datetime(2027, 1, 14, 23, 59, 59),
        "discount_type":  "percentage",
        "discount_value": Decimal("20"),
        "duration":       "once",
        "duration_months": 1,
        "eligible_plans":          None,
        "eligible_billing_cycles": None,
        "new_subscribers_only":    False,
        "max_redemptions": -1,
        "auto_apply": True,
        "is_active": True,
    },
]


# ── Seed functions ────────────────────────────────────────────────────────────

async def seed_plans_and_addons(db: AsyncSession) -> None:
    for plan_data in PLANS:
        existing = (await db.execute(
            select(Plan).where(Plan.slug == plan_data["slug"])
        )).scalar_one_or_none()
        if not existing:
            valid = {k: v for k, v in plan_data.items() if hasattr(Plan, k)}
            db.add(Plan(**valid))
            log.info("subscription.seed.plan_created", slug=plan_data["slug"])

    for addon_data in ADDONS:
        existing = (await db.execute(
            select(AddOn).where(AddOn.slug == addon_data["slug"])
        )).scalar_one_or_none()
        if not existing:
            db.add(AddOn(**addon_data))
            log.info("subscription.seed.addon_created", slug=addon_data["slug"])

    await db.commit()

    await _seed_promos(db)
    await _seed_sales(db)

    log.info("subscription.seed.complete")


async def _seed_promos(db: AsyncSession) -> None:
    for pc in PROMO_CODES:
        existing = (await db.execute(
            select(PromoCode).where(PromoCode.code == pc["code"])
        )).scalar_one_or_none()
        if not existing:
            valid = {k: v for k, v in pc.items() if hasattr(PromoCode, k)}
            db.add(PromoCode(**valid))
            log.info("subscription.seed.promo_created", code=pc["code"])
    await db.commit()


async def _seed_sales(db: AsyncSession) -> None:
    for sale in SALES:
        existing = (await db.execute(
            select(Sale).where(Sale.name == sale["name"])
        )).scalar_one_or_none()
        if not existing:
            valid = {k: v for k, v in sale.items() if hasattr(Sale, k)}
            db.add(Sale(**valid))
            log.info("subscription.seed.sale_created", name=sale["name"])
    await db.commit()

"""db/seed.py — Seed all Riviwa plans (all 15-service features) and add-ons."""
from __future__ import annotations

from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from models.subscription import AddOn, Plan

log = structlog.get_logger(__name__)

# ── Feature flag sets per plan ────────────────────────────────────────────────

_STARTER_FEATURES = dict(
    # Auth & Users
    has_2fa=False,
    has_sso=False,
    has_white_label=False,
    has_dedicated_support=False,
    has_custom_sla=False,
    # Feedback (core)
    has_employee_feedback=False,
    has_pap_registry=False,
    has_committee_mgmt=False,
    has_bulk_import=False,
    # Channels
    has_sms_channel=False,
    has_whatsapp_channel=False,
    has_phone_call_ai=False,
    # AI
    has_ai_conversation=False,
    has_ai_insights=False,
    has_voice_transcription=False,
    # Notifications
    has_push_notifications=False,
    has_whatsapp_notif=False,
    # Analytics
    has_advanced_analytics=False,
    has_custom_reports=False,
    has_spark_streaming=False,
    has_ml_predictor=False,
    # QR & Verification
    has_qr_generation=False,
    has_product_verification=False,
    has_ai_counterfeit=False,
    has_field_agents=False,
    # Staff
    has_staff_verification=False,
    has_bulk_staff_import=False,
    has_staff_analytics=False,
    # Queue
    has_queue_management=False,
    # Stakeholder
    has_stakeholder_engagement=False,
    # Translation
    has_translation=False,
    has_advanced_translation=False,
    # Integration
    has_api_access=False,
    has_webhooks=False,
    has_oauth2=False,
    has_widget_embed=False,
    has_audit_logs=False,
    # Payment
    has_payment_processing=False,
    has_paypal=False,
    has_mobile_money=False,
    # Product
    has_product_catalog=False,
    has_product_variations=False,
    has_rsin=False,
    # Recommendation
    has_recommendations=False,
    has_geo_proximity=False,
    # Waiting
    has_waiting_queue=False,
    # Advanced Auth
    has_id_verification=False,
    has_fraud_detection=False,
    has_social_login=False,
    has_multi_org=False,
)

_PROFESSIONAL_FEATURES = dict(
    # Auth & Users
    has_2fa=True,
    has_sso=False,
    has_white_label=False,
    has_dedicated_support=False,
    has_custom_sla=False,
    # Feedback (core)
    has_employee_feedback=True,
    has_pap_registry=True,
    has_committee_mgmt=False,
    has_bulk_import=False,
    # Channels
    has_sms_channel=True,
    has_whatsapp_channel=True,
    has_phone_call_ai=False,
    # AI
    has_ai_conversation=True,
    has_ai_insights=False,
    has_voice_transcription=True,
    # Notifications
    has_push_notifications=True,
    has_whatsapp_notif=True,
    # Analytics
    has_advanced_analytics=True,
    has_custom_reports=False,
    has_spark_streaming=False,
    has_ml_predictor=False,
    # QR & Verification
    has_qr_generation=True,
    has_product_verification=True,
    has_ai_counterfeit=False,
    has_field_agents=False,
    # Staff
    has_staff_verification=True,
    has_bulk_staff_import=False,
    has_staff_analytics=False,
    # Queue
    has_queue_management=False,
    # Stakeholder
    has_stakeholder_engagement=False,
    # Translation
    has_translation=True,
    has_advanced_translation=False,
    # Integration
    has_api_access=True,
    has_webhooks=False,
    has_oauth2=True,
    has_widget_embed=True,
    has_audit_logs=False,
    # Payment
    has_payment_processing=False,
    has_paypal=False,
    has_mobile_money=False,
    # Product
    has_product_catalog=True,
    has_product_variations=False,
    has_rsin=False,
    # Recommendation
    has_recommendations=True,
    has_geo_proximity=False,
    # Waiting
    has_waiting_queue=False,
    # Advanced Auth
    has_id_verification=False,
    has_fraud_detection=True,
    has_social_login=True,
    has_multi_org=True,
)

_BUSINESS_FEATURES = dict(
    # Auth & Users
    has_2fa=True,
    has_sso=False,
    has_white_label=False,
    has_dedicated_support=True,
    has_custom_sla=False,
    # Feedback (core)
    has_employee_feedback=True,
    has_pap_registry=True,
    has_committee_mgmt=True,
    has_bulk_import=True,
    # Channels
    has_sms_channel=True,
    has_whatsapp_channel=True,
    has_phone_call_ai=True,
    # AI
    has_ai_conversation=True,
    has_ai_insights=True,
    has_voice_transcription=True,
    # Notifications
    has_push_notifications=True,
    has_whatsapp_notif=True,
    # Analytics
    has_advanced_analytics=True,
    has_custom_reports=True,
    has_spark_streaming=True,
    has_ml_predictor=True,
    # QR & Verification
    has_qr_generation=True,
    has_product_verification=True,
    has_ai_counterfeit=True,
    has_field_agents=True,
    # Staff
    has_staff_verification=True,
    has_bulk_staff_import=True,
    has_staff_analytics=True,
    # Queue
    has_queue_management=True,
    # Stakeholder
    has_stakeholder_engagement=True,
    # Translation
    has_translation=True,
    has_advanced_translation=True,
    # Integration
    has_api_access=True,
    has_webhooks=True,
    has_oauth2=True,
    has_widget_embed=True,
    has_audit_logs=True,
    # Payment
    has_payment_processing=True,
    has_paypal=True,
    has_mobile_money=True,
    # Product
    has_product_catalog=True,
    has_product_variations=True,
    has_rsin=True,
    # Recommendation
    has_recommendations=True,
    has_geo_proximity=True,
    # Waiting
    has_waiting_queue=True,
    # Advanced Auth
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
        # Limits
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
    # SMS
    {"slug": "extra-sms-1k",     "name": "Extra SMS Bundle",        "description": "1,000 additional SMS notifications or AI conversations",      "type": "extra_sms",        "price_usd": Decimal("10.00"),  "unit": "1,000 SMS",   "unit_quantity": 1000},
    # Users
    {"slug": "extra-users-5",    "name": "Extra Team Members (5)",  "description": "5 additional team member seats beyond plan limit",             "type": "extra_users",      "price_usd": Decimal("25.00"),  "unit": "5 users",     "unit_quantity": 5},
    # Storage
    {"slug": "extra-storage-10g","name": "Extra Storage (10 GB)",   "description": "10 GB additional file and voice recording storage",            "type": "extra_storage",    "price_usd": Decimal("5.00"),   "unit": "10 GB",       "unit_quantity": 10},
    # API
    {"slug": "extra-api-10k",    "name": "Extra API Calls",         "description": "10,000 additional API calls per month",                        "type": "extra_api_calls",  "price_usd": Decimal("5.00"),   "unit": "10,000 calls","unit_quantity": 10000},
    # QR
    {"slug": "extra-qr-500",     "name": "Extra QR Codes (500)",    "description": "500 additional QR codes generated per month",                  "type": "extra_qr",         "price_usd": Decimal("5.00"),   "unit": "500 QR",      "unit_quantity": 500},
    # WhatsApp Business
    {"slug": "whatsapp-biz",     "name": "WhatsApp Business API",   "description": "Meta-verified WhatsApp Business sender — required for high-volume WhatsApp",  "type": "whatsapp_business","price_usd": Decimal("25.00"),  "unit": "month",       "unit_quantity": 1},
    # Custom AI
    {"slug": "custom-ai",        "name": "Custom AI Model",         "description": "Fine-tune Riviwa AI on your organisation's own data and terminology",         "type": "custom_ai",        "price_usd": Decimal("199.00"), "unit": "month",       "unit_quantity": 1},
    # Kafka
    {"slug": "dedicated-kafka",  "name": "Dedicated Kafka Cluster", "description": "Isolated event streaming cluster — for compliance or high-throughput needs",  "type": "dedicated_kafka",  "price_usd": Decimal("99.00"),  "unit": "month",       "unit_quantity": 1},
    # Translation
    {"slug": "advanced-trans",   "name": "Advanced Translation",    "description": "Cloud provider fallback (Google, DeepL, Microsoft) for all 63 languages",     "type": "advanced_translation","price_usd": Decimal("15.00"), "unit": "month",       "unit_quantity": 1},
    # Phone AI
    {"slug": "phone-ai-minutes", "name": "Phone Call AI (per min)", "description": "Twilio IVR AI voice minutes — billed on actual usage",                        "type": "phone_call_ai",    "price_usd": Decimal("0.05"),   "unit": "minute",      "unit_quantity": 1},
    # Extra projects
    {"slug": "extra-project",    "name": "Extra Project",           "description": "One additional project slot beyond plan limit",                               "type": "extra_users",      "price_usd": Decimal("10.00"),  "unit": "project",     "unit_quantity": 1},
]


async def seed_plans_and_addons(db: AsyncSession) -> None:
    for plan_data in PLANS:
        existing = (await db.execute(
            select(Plan).where(Plan.slug == plan_data["slug"])
        )).scalar_one_or_none()
        if not existing:
            # Only pass fields that exist in the Plan model
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
    log.info("subscription.seed.complete")

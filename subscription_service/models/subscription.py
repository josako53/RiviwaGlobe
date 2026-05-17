"""models/subscription.py — SQLModel ORM models for subscription_service."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, List, Optional

from sqlalchemy import Column, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


# ── Enums ─────────────────────────────────────────────────────────────────────

class BillingCycle(str, Enum):
    MONTHLY = "monthly"
    ANNUAL  = "annual"


class SubscriptionStatus(str, Enum):
    TRIALING     = "trialing"
    ACTIVE       = "active"
    PAUSED       = "paused"
    PAST_DUE     = "past_due"
    CANCELLED    = "cancelled"
    EXPIRED      = "expired"


class InvoiceStatus(str, Enum):
    DRAFT          = "draft"
    OPEN           = "open"
    PAID           = "paid"
    VOID           = "void"
    UNCOLLECTIBLE  = "uncollectible"


class PaymentMethodType(str, Enum):
    MPESA         = "mpesa"
    AZAMPAY       = "azampay"
    SELCOM        = "selcom"
    STRIPE_CARD   = "stripe_card"
    BANK_TRANSFER = "bank_transfer"


class DiscountType(str, Enum):
    PERCENTAGE   = "percentage"
    FIXED_AMOUNT = "fixed_amount"
    FREE_MONTHS  = "free_months"


class DiscountDuration(str, Enum):
    ONCE       = "once"
    REPEATING  = "repeating"
    FOREVER    = "forever"


class AddOnType(str, Enum):
    EXTRA_SMS        = "extra_sms"
    EXTRA_USERS      = "extra_users"
    EXTRA_STORAGE    = "extra_storage"
    EXTRA_API_CALLS  = "extra_api_calls"
    EXTRA_QR         = "extra_qr"
    WHATSAPP_BIZ     = "whatsapp_business"
    CUSTOM_AI        = "custom_ai"
    DEDICATED_KAFKA  = "dedicated_kafka"
    PHONE_CALL_AI    = "phone_call_ai"
    ADVANCED_TRANS   = "advanced_translation"


class SubscriptionEventType(str, Enum):
    TRIAL_STARTED      = "trial_started"
    SUBSCRIBED         = "subscribed"
    UPGRADED           = "upgraded"
    DOWNGRADED         = "downgraded"
    CANCELLED          = "cancelled"
    PAUSED             = "paused"
    RESUMED            = "resumed"
    PAYMENT_SUCCEEDED  = "payment_succeeded"
    PAYMENT_FAILED     = "payment_failed"
    DUNNED             = "dunned"
    EXPIRED            = "expired"
    PROMO_APPLIED      = "promo_applied"
    ADDON_PURCHASED    = "addon_purchased"


# ── Plan ──────────────────────────────────────────────────────────────────────

class Plan(SQLModel, table=True):
    __tablename__ = "plans"

    id:           uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    slug:         str       = Field(max_length=64, unique=True, index=True)   # starter, professional, business, enterprise
    display_name: str       = Field(max_length=128)
    tagline:      str       = Field(max_length=256, default="")
    description:  str       = Field(default="", sa_column=Column(Text))

    # Pricing (USD)
    monthly_price_usd: Decimal = Field(default=Decimal("0"), sa_column=Column(Numeric(10, 2)))
    annual_price_usd:  Decimal = Field(default=Decimal("0"), sa_column=Column(Numeric(10, 2)))  # per-month rate

    # Limits (-1 = unlimited)
    max_team_members:         int = Field(default=5)
    max_projects:             int = Field(default=3)
    max_submissions_per_month: int = Field(default=500)
    max_sms_per_month:        int = Field(default=200)
    max_api_calls_per_month:  int = Field(default=0)
    max_storage_gb:           int = Field(default=5)
    max_qr_per_month:         int = Field(default=0)
    max_staff_profiles:       int = Field(default=0)

    # Feature flags
    has_sms_channel:          bool = Field(default=False)
    has_whatsapp_channel:     bool = Field(default=False)
    has_phone_call_ai:        bool = Field(default=False)
    has_ai_conversation:      bool = Field(default=False)
    has_ai_insights:          bool = Field(default=False)
    has_voice_transcription:  bool = Field(default=False)
    has_push_notifications:   bool = Field(default=False)
    has_whatsapp_notif:       bool = Field(default=False)
    has_advanced_analytics:   bool = Field(default=False)
    has_custom_reports:       bool = Field(default=False)
    has_spark_streaming:      bool = Field(default=False)
    has_ml_predictor:         bool = Field(default=False)
    has_qr_generation:        bool = Field(default=False)
    has_product_verification: bool = Field(default=False)
    has_ai_counterfeit:       bool = Field(default=False)
    has_field_agents:         bool = Field(default=False)
    has_staff_verification:   bool = Field(default=False)
    has_queue_management:     bool = Field(default=False)
    has_stakeholder_engagement: bool = Field(default=False)
    has_translation:          bool = Field(default=False)
    has_api_access:           bool = Field(default=False)
    has_webhooks:             bool = Field(default=False)
    has_oauth2:               bool = Field(default=False)
    has_widget_embed:         bool = Field(default=False)
    has_payment_processing:   bool = Field(default=False)
    has_employee_feedback:    bool = Field(default=False)
    has_pap_registry:         bool = Field(default=False)
    has_committee_mgmt:       bool = Field(default=False)
    has_bulk_import:          bool = Field(default=False)
    has_sso:                  bool = Field(default=False)
    has_2fa:                  bool = Field(default=False)
    has_white_label:          bool = Field(default=False)
    has_dedicated_support:    bool = Field(default=False)
    has_custom_sla:           bool = Field(default=False)

    # SLA
    uptime_sla: str = Field(default="99.5%", max_length=16)

    # Meta
    trial_days:  int  = Field(default=14)
    is_active:   bool = Field(default=True)
    is_public:   bool = Field(default=True)
    sort_order:  int  = Field(default=0)
    is_custom:   bool = Field(default=False)   # Enterprise / negotiated
    extra:       Optional[Any] = Field(default=None, sa_column=Column(JSONB))
    created_at:  datetime = Field(default_factory=datetime.utcnow)
    updated_at:  datetime = Field(default_factory=datetime.utcnow)


# ── Subscription ──────────────────────────────────────────────────────────────

class Subscription(SQLModel, table=True):
    __tablename__ = "subscriptions"

    id:      uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    org_id:  uuid.UUID = Field(index=True)
    plan_id: uuid.UUID = Field(foreign_key="plans.id", index=True)

    status:        str = Field(sa_column=Column(String(32), nullable=False, index=True),
                               default=SubscriptionStatus.TRIALING.value)
    billing_cycle: str = Field(sa_column=Column(String(16), nullable=False),
                               default=BillingCycle.MONTHLY.value)

    current_period_start: datetime = Field(default_factory=datetime.utcnow)
    current_period_end:   datetime = Field(default_factory=datetime.utcnow)
    trial_start:          Optional[datetime] = Field(default=None)
    trial_end:            Optional[datetime] = Field(default=None)

    cancel_at_period_end: bool              = Field(default=False)
    cancelled_at:         Optional[datetime] = Field(default=None)
    cancellation_reason:  Optional[str]     = Field(default=None, max_length=512)

    paused_at:       Optional[datetime] = Field(default=None)
    pause_resume_at: Optional[datetime] = Field(default=None)

    promo_code_id:           Optional[uuid.UUID] = Field(default=None)
    discount_pct:            Decimal = Field(default=Decimal("0"), sa_column=Column(Numeric(5, 2)))
    discount_months_remaining: int   = Field(default=0)

    default_payment_method_id: Optional[uuid.UUID] = Field(default=None)

    # Effective price (may differ from plan if grandfathered)
    effective_monthly_usd: Decimal = Field(default=Decimal("0"), sa_column=Column(Numeric(10, 2)))

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ── Invoice ───────────────────────────────────────────────────────────────────

class Invoice(SQLModel, table=True):
    __tablename__ = "invoices"

    id:              uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    invoice_number:  str       = Field(max_length=32, unique=True, index=True)
    org_id:          uuid.UUID = Field(index=True)
    subscription_id: uuid.UUID = Field(foreign_key="subscriptions.id", index=True)

    status: str = Field(sa_column=Column(String(32), nullable=False, index=True),
                        default=InvoiceStatus.OPEN.value)

    subtotal_usd: Decimal = Field(default=Decimal("0"), sa_column=Column(Numeric(10, 2)))
    discount_usd: Decimal = Field(default=Decimal("0"), sa_column=Column(Numeric(10, 2)))
    tax_usd:      Decimal = Field(default=Decimal("0"), sa_column=Column(Numeric(10, 2)))
    total_usd:    Decimal = Field(default=Decimal("0"), sa_column=Column(Numeric(10, 2)))
    currency:     str     = Field(default="USD", max_length=8)

    billing_period_start: datetime = Field(default_factory=datetime.utcnow)
    billing_period_end:   datetime = Field(default_factory=datetime.utcnow)
    due_date:             datetime = Field(default_factory=datetime.utcnow)
    paid_at:              Optional[datetime] = Field(default=None)

    payment_method_type: Optional[str] = Field(default=None, max_length=32)
    payment_reference:   Optional[str] = Field(default=None, max_length=256)

    line_items: Optional[Any] = Field(default=None, sa_column=Column(JSONB))
    pdf_url:    Optional[str] = Field(default=None, max_length=512)

    retry_count:     int            = Field(default=0)
    next_retry_at:   Optional[datetime] = Field(default=None)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ── PaymentMethod ─────────────────────────────────────────────────────────────

class PaymentMethod(SQLModel, table=True):
    __tablename__ = "payment_methods"

    id:     uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    org_id: uuid.UUID = Field(index=True)

    type:         str  = Field(sa_column=Column(String(32), nullable=False))
    is_default:   bool = Field(default=False)
    display_name: str  = Field(max_length=128, default="")

    # Mobile money
    phone_number: Optional[str] = Field(default=None, max_length=32)

    # Card
    card_last4:     Optional[str] = Field(default=None, max_length=4)
    card_brand:     Optional[str] = Field(default=None, max_length=32)
    card_exp_month: Optional[int] = Field(default=None)
    card_exp_year:  Optional[int] = Field(default=None)

    # Provider reference
    provider_ref: Optional[str] = Field(default=None, max_length=256)
    provider_meta: Optional[Any] = Field(default=None, sa_column=Column(JSONB))

    is_active:  bool     = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ── PromoCode ─────────────────────────────────────────────────────────────────

class PromoCode(SQLModel, table=True):
    __tablename__ = "promo_codes"

    id:   uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    code: str       = Field(max_length=64, unique=True, index=True)
    name: str       = Field(max_length=128)
    description: str = Field(default="", sa_column=Column(Text))

    discount_type:  str     = Field(sa_column=Column(String(32), nullable=False))
    discount_value: Decimal = Field(default=Decimal("0"), sa_column=Column(Numeric(10, 2)))

    duration:        str = Field(sa_column=Column(String(32), nullable=False), default="once")
    duration_months: int = Field(default=1)

    max_redemptions:  int = Field(default=-1)   # -1 = unlimited
    redemption_count: int = Field(default=0)

    eligible_plans:        Optional[Any] = Field(default=None, sa_column=Column(JSONB))  # list of plan slugs
    new_subscribers_only:  bool = Field(default=True)
    min_plan_price_usd:    Decimal = Field(default=Decimal("0"), sa_column=Column(Numeric(10, 2)))

    expires_at:  Optional[datetime] = Field(default=None)
    is_active:   bool               = Field(default=True)
    created_by:  Optional[uuid.UUID] = Field(default=None)
    created_at:  datetime = Field(default_factory=datetime.utcnow)


class PromoRedemption(SQLModel, table=True):
    __tablename__ = "promo_redemptions"

    id:              uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    promo_code_id:   uuid.UUID = Field(foreign_key="promo_codes.id", index=True)
    org_id:          uuid.UUID = Field(index=True)
    subscription_id: uuid.UUID = Field(foreign_key="subscriptions.id")
    redeemed_at:     datetime  = Field(default_factory=datetime.utcnow)


# ── UsageMeter ────────────────────────────────────────────────────────────────

class UsageMeter(SQLModel, table=True):
    __tablename__ = "usage_meters"

    id:              uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    org_id:          uuid.UUID = Field(index=True)
    subscription_id: uuid.UUID = Field(foreign_key="subscriptions.id", index=True)
    period_start:    datetime  = Field(index=True)
    period_end:      datetime  = Field(index=True)

    submissions_count:   int = Field(default=0)
    sms_count:           int = Field(default=0)
    api_calls_count:     int = Field(default=0)
    storage_bytes:       int = Field(default=0)
    qr_codes_count:      int = Field(default=0)
    team_members_count:  int = Field(default=0)
    staff_profiles_count: int = Field(default=0)

    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ── AddOn ─────────────────────────────────────────────────────────────────────

class AddOn(SQLModel, table=True):
    __tablename__ = "addons"

    id:            uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    slug:          str       = Field(max_length=64, unique=True, index=True)
    name:          str       = Field(max_length=128)
    description:   str       = Field(default="", sa_column=Column(Text))
    type:          str       = Field(sa_column=Column(String(64), nullable=False))
    price_usd:     Decimal   = Field(sa_column=Column(Numeric(10, 2)))
    unit:          str       = Field(max_length=64, default="")
    unit_quantity: int       = Field(default=1)
    is_active:     bool      = Field(default=True)
    created_at:    datetime  = Field(default_factory=datetime.utcnow)


class OrgAddOn(SQLModel, table=True):
    __tablename__ = "org_addons"

    id:              uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    org_id:          uuid.UUID = Field(index=True)
    subscription_id: uuid.UUID = Field(foreign_key="subscriptions.id", index=True)
    addon_id:        uuid.UUID = Field(foreign_key="addons.id")
    quantity:        int       = Field(default=1)
    purchased_at:    datetime  = Field(default_factory=datetime.utcnow)
    expires_at:      Optional[datetime] = Field(default=None)
    status:          str       = Field(default="active", max_length=32)


# ── SubscriptionEvent ─────────────────────────────────────────────────────────

class SubscriptionEvent(SQLModel, table=True):
    __tablename__ = "subscription_events"

    id:              uuid.UUID        = Field(default_factory=uuid.uuid4, primary_key=True)
    org_id:          uuid.UUID        = Field(index=True)
    subscription_id: uuid.UUID        = Field(foreign_key="subscriptions.id", index=True)
    event_type:      str              = Field(sa_column=Column(String(64), nullable=False, index=True))
    from_plan_id:    Optional[uuid.UUID] = Field(default=None)
    to_plan_id:      Optional[uuid.UUID] = Field(default=None)
    actor_id:        Optional[uuid.UUID] = Field(default=None)
    actor_type:      str              = Field(default="org", max_length=32)   # org | admin | system
    metadata:        Optional[Any]    = Field(default=None, sa_column=Column(JSONB))
    created_at:      datetime         = Field(default_factory=datetime.utcnow, index=True)


# ── DunningAttempt ────────────────────────────────────────────────────────────

class DunningAttempt(SQLModel, table=True):
    __tablename__ = "dunning_attempts"

    id:              uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    org_id:          uuid.UUID = Field(index=True)
    subscription_id: uuid.UUID = Field(foreign_key="subscriptions.id", index=True)
    invoice_id:      uuid.UUID = Field(foreign_key="invoices.id", index=True)
    attempt_number:  int       = Field(default=1)
    attempted_at:    datetime  = Field(default_factory=datetime.utcnow)
    next_retry_at:   Optional[datetime] = Field(default=None)
    succeeded:       bool      = Field(default=False)
    error_message:   Optional[str] = Field(default=None, max_length=512)

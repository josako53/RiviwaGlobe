"""
models/payment.py — payment_service
═══════════════════════════════════════════════════════════════════════════════
Tables
───────
  Payment          — the intent: what is being paid, by whom, how much
  PaymentTransaction — one attempt to settle a Payment via a provider
  WebhookLog       — raw inbound callbacks from payment gateways (audit trail)

Design
───────
  A Payment can have multiple Transactions (retries, refunds).
  The final settled Transaction sets Payment.status → PAID.

  Providers:
    azampay   — AzamPay (supports Airtel TZ, CRDB, NMB, MPESA via AzamPay)
    selcom    — Selcom Mobile (Tigo Pesa, TTCL Pesa, Halotel)
    mpesa     — Vodacom M-Pesa Tanzania (direct integration)

  Payment types:
    grievance_fee       — rare; some Consumer registration charges
    project_contribution — community contribution to a sub-project
    service_fee         — org service access fees
    subscription        — platform subscription (org monthly/annual)
    refund              — outbound refund to Consumer/org
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from sqlalchemy import Column, DateTime, Enum as SAEnum, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel


class PaymentProvider(str, Enum):
    AZAMPAY = "azampay"
    SELCOM  = "selcom"
    MPESA   = "mpesa"
    PAYPAL  = "paypal"
    AIRTEL  = "airtel"
    YAS     = "yas"


class PaymentStatus(str, Enum):
    PENDING    = "pending"     # created, awaiting initiation
    INITIATED  = "initiated"   # sent to provider, awaiting Consumer action
    PROCESSING = "processing"  # Consumer actioned, provider processing
    PAID       = "paid"        # confirmed paid
    FAILED     = "failed"      # provider rejected
    EXPIRED    = "expired"     # timeout with no action
    REFUNDED   = "refunded"    # money returned to payer
    CANCELLED  = "cancelled"   # cancelled before initiation


class PaymentType(str, Enum):
    GRIEVANCE_FEE        = "grievance_fee"
    PROJECT_CONTRIBUTION = "project_contribution"
    SERVICE_FEE          = "service_fee"
    SUBSCRIPTION         = "subscription"
    REFUND               = "refund"


class TransactionStatus(str, Enum):
    PENDING    = "pending"
    SUCCESS    = "success"
    FAILED     = "failed"
    TIMEOUT    = "timeout"
    REVERSED   = "reversed"


class Currency(str, Enum):
    TZS = "TZS"
    USD = "USD"
    KES = "KES"


class DisbursementStatus(str, Enum):
    PENDING    = "pending"    # created, not yet sent to Airtel
    PROCESSING = "processing" # sent to Airtel, awaiting confirmation
    SUCCESS    = "success"    # TS — Airtel confirmed funds delivered
    FAILED     = "failed"     # TF — Airtel rejected or failed
    AMBIGUOUS  = "ambiguous"  # TA — unclear state; re-enquire after 1 min
    CANCELLED  = "cancelled"  # cancelled before sending


class DisbursementType(str, Enum):
    B2B = "B2B"  # business-to-business (internal staff payments, default)
    B2C = "B2C"  # business-to-consumer (direct consumer payouts)


# ─────────────────────────────────────────────────────────────────────────────

class Payment(SQLModel, table=True):
    """
    A payment intent — what should be paid, by whom, for what.

    One Payment can have 1-N PaymentTransactions (e.g. first attempt fails,
    Consumer retries on a different channel — same Payment, new Transaction).
    Status transitions to PAID when any Transaction succeeds.

    Cross-service soft links (no FK constraints):
      payer_user_id     → auth_service User.id
      org_id            → auth_service Organisation.id
      project_id        → auth_service OrgProject.id  (or feedback_service ProjectCache.id)
      reference_id      → any domain object (feedback item, invoice, sub-project)
    """
    __tablename__ = "payments"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)

    # ── What is being paid ────────────────────────────────────────────────────
    payment_type:   PaymentType = Field(
        sa_column=Column(SAEnum(PaymentType, name="payment_type"), nullable=False, index=True)
    )
    amount:         float = Field(nullable=False, description="Amount in minor units (e.g. TZS cents).")
    currency:       Currency = Field(
        default=Currency.TZS,
        sa_column=Column(SAEnum(Currency, name="payment_currency"), nullable=False),
    )
    description:    Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))

    # ── Who is paying ─────────────────────────────────────────────────────────
    payer_user_id:  Optional[uuid.UUID] = Field(
        default=None, nullable=True, index=True,
        description="auth_service User.id of the payer.",
    )
    payer_phone:    Optional[str] = Field(
        default=None, max_length=20, nullable=True,
        description="E.164 phone number used for mobile money.",
    )
    payer_name:     Optional[str] = Field(default=None, max_length=200, nullable=True)
    payer_email:    Optional[str] = Field(default=None, max_length=255, nullable=True)

    # ── Context: what this payment is for ─────────────────────────────────────
    org_id:         Optional[uuid.UUID] = Field(default=None, nullable=True, index=True)
    project_id:     Optional[uuid.UUID] = Field(default=None, nullable=True, index=True)
    reference_id:   Optional[uuid.UUID] = Field(
        default=None, nullable=True, index=True,
        description="ID of the domain object this payment is for (invoice, sub-project, etc.)",
    )
    reference_type: Optional[str] = Field(
        default=None, max_length=50, nullable=True,
        description="Type of reference: 'invoice' | 'subproject' | 'subscription' | 'feedback'",
    )

    # ── Status ────────────────────────────────────────────────────────────────
    status: PaymentStatus = Field(
        default=PaymentStatus.PENDING,
        sa_column=Column(SAEnum(PaymentStatus, name="payment_status"), nullable=False, index=True),
    )
    external_ref:   Optional[str] = Field(
        default=None, max_length=255, nullable=True, index=True,
        description="Our unique reference sent to the provider. Used to match callbacks.",
    )

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_by_user_id: Optional[uuid.UUID] = Field(default=None, nullable=True)
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"),
                         onupdate=text("now()"), nullable=False)
    )
    paid_at:    Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    expires_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )

    transactions: PaymentTransaction = Relationship(back_populates="payment")

    def __repr__(self):
        return f"<Payment {self.amount} {self.currency} [{self.status}]>"


# ─────────────────────────────────────────────────────────────────────────────

class PaymentTransaction(SQLModel, table=True):
    """
    One provider transaction attempt for a Payment.

    Stores full provider request/response for audit and debugging.
    provider_payload (JSONB) stores the raw provider response so we can
    replay or investigate without hitting the provider again.
    """
    __tablename__ = "payment_transactions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)

    payment_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("payments.id", ondelete="CASCADE"), nullable=False, index=True)
    )

    provider: PaymentProvider = Field(
        sa_column=Column(SAEnum(PaymentProvider, name="transaction_provider"), nullable=False, index=True)
    )
    status: TransactionStatus = Field(
        default=TransactionStatus.PENDING,
        sa_column=Column(SAEnum(TransactionStatus, name="transaction_status"), nullable=False, index=True),
    )

    # Provider-assigned identifiers
    provider_ref:       Optional[str] = Field(default=None, max_length=255, nullable=True, index=True)
    provider_order_id:  Optional[str] = Field(default=None, max_length=255, nullable=True)
    provider_receipt:   Optional[str] = Field(default=None, max_length=255, nullable=True)

    # Raw provider exchange
    provider_request:  Optional[Dict[str, Any]] = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
    provider_response: Optional[Dict[str, Any]] = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )

    # Settled amount (may differ from requested if partial)
    settled_amount:   Optional[float] = Field(default=None, nullable=True)
    failure_reason:   Optional[str]   = Field(default=None, sa_column=Column(Text, nullable=True))

    # Timestamps
    initiated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )
    completed_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )

    payment: Payment = Relationship(back_populates="transactions")

    def __repr__(self):
        return f"<PaymentTransaction {self.provider} [{self.status}]>"


# ─────────────────────────────────────────────────────────────────────────────

class WebhookLog(SQLModel, table=True):
    """
    Raw inbound webhook payloads from payment gateways.
    Logged before any processing — essential audit trail and replay source.
    """
    __tablename__ = "webhook_logs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)

    provider:     PaymentProvider = Field(
        sa_column=Column(SAEnum(PaymentProvider, name="webhook_provider"), nullable=False, index=True)
    )
    headers:      Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSONB, nullable=True))
    body:         Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSONB, nullable=True))
    raw_body:     Optional[str]            = Field(default=None, sa_column=Column(Text, nullable=True))
    # Matched transaction if we could resolve it
    transaction_id: Optional[uuid.UUID]   = Field(
        sa_column=Column(ForeignKey("payment_transactions.id", ondelete="SET NULL"), nullable=True, index=True)
    )
    processed:    bool    = Field(default=False, nullable=False)
    process_error: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    received_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )


# ─────────────────────────────────────────────────────────────────────────────

class Disbursement(SQLModel, table=True):
    """
    Outbound Airtel Money disbursement — platform admin / org owner only.

    Used to pay internal staff, agents, or approved recipients directly to
    their Airtel Money wallet. Restricted to B2B by default; B2C requires
    explicit type override.

    Airtel V2 Disbursements API:
      POST /standard/v2/disbursements/          — send funds
      GET  /standard/v2/disbursements/{txn_id}  — enquiry (poll after ≥1 min)

    Status lifecycle: PENDING → PROCESSING → SUCCESS | FAILED | AMBIGUOUS
      AMBIGUOUS means Airtel returned TA — re-enquire to get final status.
    """
    __tablename__ = "disbursements"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)

    # ── Recipient ─────────────────────────────────────────────────────────────
    payee_msisdn: str = Field(
        max_length=15, nullable=False,
        description="Airtel phone number WITHOUT country code, e.g. '756789012'",
    )
    payee_name: Optional[str] = Field(default=None, max_length=200, nullable=True)

    # ── Transfer details ──────────────────────────────────────────────────────
    amount:           float  = Field(nullable=False)
    currency:         str    = Field(default="TZS", max_length=5, nullable=False)
    reference:        str    = Field(max_length=255, nullable=False,
                                    description="Reference sent to Airtel — shown on recipient's receipt")
    description:      Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    transaction_type: str    = Field(default="B2B", max_length=5, nullable=False,
                                    description="B2B (internal staff) or B2C (consumer payout)")

    # ── Context ───────────────────────────────────────────────────────────────
    org_id:     Optional[uuid.UUID] = Field(default=None, nullable=True, index=True)
    notes:      Optional[str]       = Field(default=None, sa_column=Column(Text, nullable=True),
                                           description="Internal admin notes — not sent to Airtel")

    # ── Status ────────────────────────────────────────────────────────────────
    status: str = Field(
        default=DisbursementStatus.PENDING.value,
        sa_column=Column(String(20), nullable=False, index=True),
    )

    # ── Airtel transaction identifiers ────────────────────────────────────────
    our_transaction_id:  str            = Field(
        max_length=64, nullable=False, index=True,
        description="UUID we generate and send as transaction.id — used for enquiry",
    )
    airtel_money_id:     Optional[str]  = Field(default=None, max_length=255, nullable=True,
                                                description="Airtel-generated airtel_money_id from disbursement response")
    airtel_reference_id: Optional[str]  = Field(default=None, max_length=255, nullable=True,
                                                description="Airtel-generated reference_id from disbursement response")
    failure_reason:      Optional[str]  = Field(default=None, sa_column=Column(Text, nullable=True))
    raw_response:        Optional[Dict[str, Any]] = Field(
        default=None, sa_column=Column(JSONB, nullable=True),
        description="Full Airtel API response — stored for audit and replay",
    )

    # ── Audit ─────────────────────────────────────────────────────────────────
    initiated_by: uuid.UUID = Field(
        nullable=False, index=True,
        description="auth_service User.id of the admin who created this disbursement",
    )
    created_at:   datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    )
    updated_at:   datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=text("now()"),
                         onupdate=text("now()"), nullable=False)
    )
    completed_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )

    def __repr__(self):
        return f"<Disbursement {self.amount} TZS → {self.payee_msisdn} [{self.status}]>"

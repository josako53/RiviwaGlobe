"""services/payment_service.py — payment_service"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select as sm_select

from core.exceptions import (
    DuplicatePaymentError, NotFoundError, PaymentNotFoundError,
    TransactionNotFoundError, ValidationError,
)
from models.payment import (
    Currency, Payment, PaymentProvider, PaymentStatus,
    PaymentTransaction, PaymentType, TransactionStatus, WebhookLog,
)
from providers import get_provider

log = structlog.get_logger(__name__)

_PAYMENT_EXPIRY_HOURS = {
    PaymentType.GRIEVANCE_FEE:        24,
    PaymentType.PROJECT_CONTRIBUTION: 48,
    PaymentType.SERVICE_FEE:          24,
    PaymentType.SUBSCRIPTION:         72,
    PaymentType.REFUND:               48,
}


class PaymentService:

    def __init__(self, db: AsyncSession, publisher=None) -> None:
        self.db        = db
        self.publisher = publisher

    # ── Create ────────────────────────────────────────────────────────────────

    async def create_payment(
        self,
        payment_type:   PaymentType,
        amount:         float,
        currency:       Currency,
        phone:          str,
        payer_user_id:  Optional[uuid.UUID] = None,
        payer_name:     Optional[str]       = None,
        payer_email:    Optional[str]       = None,
        description:    Optional[str]       = None,
        org_id:         Optional[uuid.UUID] = None,
        project_id:     Optional[uuid.UUID] = None,
        reference_id:   Optional[uuid.UUID] = None,
        reference_type: Optional[str]       = None,
        created_by:     Optional[uuid.UUID] = None,
    ) -> Payment:
        if amount <= 0:
            raise ValidationError("amount must be positive.")

        # Generate external ref (sent to provider as our idempotency key)
        external_ref = f"RVW-{uuid.uuid4().hex[:12].upper()}"

        expiry_h  = _PAYMENT_EXPIRY_HOURS.get(payment_type, 24)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=expiry_h)

        payment = Payment(
            payment_type        = payment_type,
            amount              = amount,
            currency            = currency,
            description         = description,
            payer_user_id       = payer_user_id,
            payer_phone         = phone,
            payer_name          = payer_name,
            payer_email         = payer_email,
            org_id              = org_id,
            project_id          = project_id,
            reference_id        = reference_id,
            reference_type      = reference_type,
            external_ref        = external_ref,
            status              = PaymentStatus.PENDING,
            created_by_user_id  = created_by,
            expires_at          = expires_at,
        )
        self.db.add(payment)
        await self.db.flush()
        await self.db.refresh(payment)
        await self.db.commit()
        log.info("payment.created", payment_id=str(payment.id), amount=amount,
                 type=payment_type.value, phone=phone[:6]+"****")
        return payment

    # ── Initiate via provider ─────────────────────────────────────────────────

    async def initiate(
        self,
        payment_id: uuid.UUID,
        provider:   PaymentProvider,
    ) -> PaymentTransaction:
        """
        Send payment request to the chosen provider.
        Creates a PaymentTransaction. Payment.status → INITIATED.
        """
        payment = await self._get_payment(payment_id)
        if payment.status not in (PaymentStatus.PENDING, PaymentStatus.FAILED):
            raise ValidationError(
                f"Cannot initiate payment with status '{payment.status.value}'. "
                "Only PENDING or FAILED payments can be re-initiated."
            )
        if not payment.payer_phone:
            raise ValidationError("payer_phone is required to initiate a payment.")

        prov = get_provider(provider)
        try:
            result = await prov.initiate(payment, payment.payer_phone)
        except Exception as exc:
            # Record the failure
            txn = PaymentTransaction(
                payment_id      = payment_id,
                provider        = provider,
                status          = TransactionStatus.FAILED,
                failure_reason  = str(exc),
                completed_at    = datetime.now(timezone.utc),
            )
            self.db.add(txn)
            payment.status = PaymentStatus.FAILED
            self.db.add(payment)
            await self.db.commit()
            raise

        txn = PaymentTransaction(
            payment_id         = payment_id,
            provider           = provider,
            status             = TransactionStatus.PENDING,
            provider_ref       = result.get("provider_ref"),
            provider_order_id  = result.get("provider_order_id"),
            provider_response  = result.get("provider_response"),
        )
        self.db.add(txn)
        payment.status = PaymentStatus.INITIATED
        self.db.add(payment)
        await self.db.flush()
        await self.db.refresh(txn)
        await self.db.commit()

        log.info("payment.initiated", payment_id=str(payment_id),
                 provider=provider.value, txn_id=str(txn.id))
        return txn

    # ── Verify ────────────────────────────────────────────────────────────────

    async def verify(self, transaction_id: uuid.UUID) -> PaymentTransaction:
        """Poll provider for transaction status and update accordingly."""
        txn = await self._get_transaction(transaction_id)
        if txn.status in (TransactionStatus.SUCCESS, TransactionStatus.REVERSED):
            return txn  # already final
        if not txn.provider_ref:
            raise ValidationError("Transaction has no provider_ref to verify.")

        prov   = get_provider(txn.provider)
        result = await prov.verify(txn.provider_ref)
        status = result.get("status", "pending")

        txn.provider_response = result.get("provider_response", txn.provider_response)

        if status == "success":
            txn.status       = TransactionStatus.SUCCESS
            txn.completed_at = datetime.now(timezone.utc)
            txn.provider_receipt = result.get("receipt")
            # Update parent payment
            payment          = await self._get_payment(txn.payment_id)
            payment.status   = PaymentStatus.PAID
            payment.paid_at  = datetime.now(timezone.utc)
            self.db.add(payment)
            log.info("payment.paid", payment_id=str(txn.payment_id),
                     txn_id=str(transaction_id))
            # Publish event
            if self.publisher:
                try:
                    await self.publisher.payment_completed(
                        txn.payment_id, txn.provider.value, payment.amount
                    )
                except Exception as e:
                    log.error("payment.publish_failed", error=str(e))

        elif status == "failed":
            txn.status       = TransactionStatus.FAILED
            txn.completed_at = datetime.now(timezone.utc)
            txn.failure_reason = result.get("reason", "Provider declined")
            payment = await self._get_payment(txn.payment_id)
            payment.status = PaymentStatus.FAILED
            self.db.add(payment)

        self.db.add(txn)
        await self.db.commit()
        return txn

    # ── Process webhook ───────────────────────────────────────────────────────

    async def process_webhook(
        self,
        provider:  PaymentProvider,
        headers:   dict,
        body:      dict,
        raw_body:  str,
    ) -> WebhookLog:
        """
        Log a raw inbound webhook and try to reconcile it with a transaction.
        Always logs regardless of processing result — audit trail.
        """
        # Attempt to extract provider_ref from payload
        provider_ref = (
            body.get("transactionId")                    # AzamPay
            or body.get("order_id")                      # Selcom
            or body.get("output_ConversationID")         # M-Pesa
            or body.get("reference")
        )

        # Find matching transaction
        txn_id = None
        if provider_ref:
            result = await self.db.execute(
                sm_select(PaymentTransaction).where(
                    PaymentTransaction.provider_ref == provider_ref
                )
            )
            txn = result.scalar_one_or_none()
            if txn:
                txn_id = txn.id

        wh = WebhookLog(
            provider       = provider,
            headers        = headers,
            body           = body,
            raw_body       = raw_body,
            transaction_id = txn_id,
        )
        self.db.add(wh)
        await self.db.flush()

        # Reconcile if transaction found
        error = None
        if txn_id:
            try:
                await self.verify(txn_id)
                wh.processed = True
            except Exception as exc:
                error = str(exc)
                wh.process_error = error
                log.error("payment.webhook.reconcile_failed",
                          txn_id=str(txn_id), error=error)

        self.db.add(wh)
        await self.db.commit()
        return wh

    # ── Refund ────────────────────────────────────────────────────────────────

    async def refund(self, payment_id: uuid.UUID) -> PaymentTransaction:
        payment = await self._get_payment(payment_id)
        if payment.status != PaymentStatus.PAID:
            raise ValidationError("Only PAID payments can be refunded.")

        # Find the successful transaction
        result = await self.db.execute(
            sm_select(PaymentTransaction).where(
                PaymentTransaction.payment_id == payment_id,
                PaymentTransaction.status     == TransactionStatus.SUCCESS,
            )
        )
        txn = result.scalar_one_or_none()
        if not txn:
            raise TransactionNotFoundError()

        prov   = get_provider(txn.provider)
        result = await prov.refund(txn)

        refund_txn = PaymentTransaction(
            payment_id      = payment_id,
            provider        = txn.provider,
            status          = TransactionStatus.SUCCESS if result.get("status") == "success" else TransactionStatus.FAILED,
            failure_reason  = result.get("reason"),
            completed_at    = datetime.now(timezone.utc),
            provider_response = result.get("provider_response"),
        )
        self.db.add(refund_txn)
        payment.status = PaymentStatus.REFUNDED
        self.db.add(payment)
        await self.db.commit()
        return refund_txn

    # ── Queries ───────────────────────────────────────────────────────────────

    async def get_payment(self, payment_id: uuid.UUID) -> Payment:
        return await self._get_payment(payment_id)

    async def list_payments(
        self,
        payer_user_id: Optional[uuid.UUID] = None,
        org_id:        Optional[uuid.UUID] = None,
        project_id:    Optional[uuid.UUID] = None,
        reference_id:  Optional[uuid.UUID] = None,
        status:        Optional[str]       = None,
        payment_type:  Optional[str]       = None,
        skip: int = 0, limit: int = 50,
    ) -> list[Payment]:
        q = sm_select(Payment)
        if payer_user_id: q = q.where(Payment.payer_user_id == payer_user_id)
        if org_id:        q = q.where(Payment.org_id        == org_id)
        if project_id:    q = q.where(Payment.project_id    == project_id)
        if reference_id:  q = q.where(Payment.reference_id  == reference_id)
        if status:        q = q.where(Payment.status        == status)
        if payment_type:  q = q.where(Payment.payment_type  == payment_type)
        q = q.order_by(Payment.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def get_transaction(self, txn_id: uuid.UUID) -> PaymentTransaction:
        return await self._get_transaction(txn_id)

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _get_payment(self, payment_id: uuid.UUID) -> Payment:
        result = await self.db.execute(
            sm_select(Payment).where(Payment.id == payment_id)
        )
        payment = result.scalar_one_or_none()
        if not payment:
            raise PaymentNotFoundError()
        return payment

    async def _get_transaction(self, txn_id: uuid.UUID) -> PaymentTransaction:
        result = await self.db.execute(
            sm_select(PaymentTransaction).where(PaymentTransaction.id == txn_id)
        )
        txn = result.scalar_one_or_none()
        if not txn:
            raise TransactionNotFoundError()
        return txn

"""
services/payment_service.py
────────────────────────────────────────────────────────────────────────────
Business logic for the full payment lifecycle:
  create → initiate → verify → refund / cancel.

Orchestrates PaymentRepository, provider implementations, and Kafka events.
Owns all validation rules. Never touches the DB directly.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import structlog

from core.exceptions import (
    DuplicatePaymentError,
    PaymentNotFoundError,
    PaymentProviderError,
    TransactionNotFoundError,
    ValidationError,
)
from events.producer import PaymentProducer
from models.payment import (
    Currency,
    Payment,
    PaymentProvider,
    PaymentStatus,
    PaymentTransaction,
    PaymentType,
    TransactionStatus,
    WebhookLog,
)
from providers import get_provider
from repositories.payment_repository import PaymentRepository
from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger(__name__)

_EXPIRY_HOURS: dict[PaymentType, int] = {
    PaymentType.GRIEVANCE_FEE:        24,
    PaymentType.PROJECT_CONTRIBUTION: 48,
    PaymentType.SERVICE_FEE:          24,
    PaymentType.SUBSCRIPTION:         72,
    PaymentType.REFUND:               48,
}


class PaymentService:

    def __init__(self, db: AsyncSession, producer: Optional[PaymentProducer] = None) -> None:
        self.repo     = PaymentRepository(db)
        self.producer = producer
        self.db       = db

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

        external_ref = f"RVW-{uuid.uuid4().hex[:12].upper()}"
        expires_at   = datetime.now(timezone.utc) + timedelta(hours=_EXPIRY_HOURS.get(payment_type, 24))

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
        payment = await self.repo.create_payment(payment)
        await self.db.commit()

        log.info("payment.created", payment_id=str(payment.id),
                 amount=amount, type=payment_type.value, phone=phone[:6] + "****")
        return payment

    # ── Initiate ──────────────────────────────────────────────────────────────

    async def initiate(
        self,
        payment_id: uuid.UUID,
        provider:   PaymentProvider,
    ) -> PaymentTransaction:
        """Send payment request to the chosen provider. Creates a PaymentTransaction."""
        payment = await self._get_payment_or_404(payment_id)

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
        except PaymentProviderError:
            # Record failed attempt
            failed_txn = PaymentTransaction(
                payment_id     = payment_id,
                provider       = provider,
                status         = TransactionStatus.FAILED,
                completed_at   = datetime.now(timezone.utc),
            )
            await self.repo.create_transaction(failed_txn)
            payment.status = PaymentStatus.FAILED
            await self.repo.save_payment(payment)
            await self.db.commit()
            raise

        txn = PaymentTransaction(
            payment_id        = payment_id,
            provider          = provider,
            status            = TransactionStatus.PENDING,
            provider_ref      = result.get("provider_ref"),
            provider_order_id = result.get("provider_order_id"),
            provider_response = result.get("provider_response"),
        )
        txn = await self.repo.create_transaction(txn)
        payment.status = PaymentStatus.INITIATED
        await self.repo.save_payment(payment)
        await self.db.commit()

        log.info("payment.initiated", payment_id=str(payment_id),
                 provider=provider.value, txn_id=str(txn.id))

        # Publish event
        if self.producer:
            try:
                await self.producer.payment_initiated(payment, provider.value)
            except Exception as e:
                log.error("payment.publish_failed", error=str(e))

        return txn

    # ── Verify ────────────────────────────────────────────────────────────────

    async def verify(self, transaction_id: uuid.UUID) -> PaymentTransaction:
        """Poll provider for latest status and update accordingly."""
        txn = await self._get_transaction_or_404(transaction_id)

        if txn.status in (TransactionStatus.SUCCESS, TransactionStatus.REVERSED):
            return txn  # Already final

        if not txn.provider_ref:
            raise ValidationError("Transaction has no provider_ref to verify.")

        prov   = get_provider(txn.provider)
        result = await prov.verify(txn.provider_ref)
        status = result.get("status", "pending")

        txn.provider_response = result.get("provider_response", txn.provider_response)

        if status == "success":
            txn.status        = TransactionStatus.SUCCESS
            txn.completed_at  = datetime.now(timezone.utc)
            txn.provider_receipt = result.get("receipt")

            payment        = await self._get_payment_or_404(txn.payment_id)
            payment.status = PaymentStatus.PAID
            payment.paid_at = datetime.now(timezone.utc)
            await self.repo.save_payment(payment)

            log.info("payment.paid", payment_id=str(txn.payment_id), txn_id=str(transaction_id))

            if self.producer:
                try:
                    await self.producer.payment_completed(txn.payment_id, txn.provider.value, payment.amount)
                except Exception as e:
                    log.error("payment.publish_failed", error=str(e))

            # Notify the payer — payment confirmed
            try:
                await self.producer.notifications.payment_confirmed(
                    payment_id        = str(txn.payment_id),
                    recipient_user_id = str(payment.payer_user_id) if payment.payer_user_id else None,
                    recipient_phone   = payment.payer_phone,
                    amount            = float(payment.amount),
                    currency          = payment.currency or "TZS",
                    description       = payment.description or "Riviwa payment",
                )
            except Exception as _exc:
                log.warning("payment.confirmed_notification_failed", error=str(_exc))

        elif status == "failed":
            txn.status       = TransactionStatus.FAILED
            txn.completed_at = datetime.now(timezone.utc)
            txn.failure_reason = result.get("reason", "Provider declined")

            payment        = await self._get_payment_or_404(txn.payment_id)
            payment.status = PaymentStatus.FAILED
            await self.repo.save_payment(payment)

            # Notify the payer — payment failed
            try:
                await self.producer.notifications.payment_failed(
                    payment_id        = str(txn.payment_id),
                    recipient_user_id = str(payment.payer_user_id) if payment.payer_user_id else None,
                    recipient_phone   = payment.payer_phone,
                    amount            = float(payment.amount),
                    currency          = payment.currency or "TZS",
                    reason            = txn.failure_reason or "Payment could not be processed.",
                )
            except Exception as _exc:
                log.warning("payment.failed_notification_failed", error=str(_exc))

        await self.repo.save_transaction(txn)
        await self.db.commit()
        return txn

    # ── Webhook ───────────────────────────────────────────────────────────────

    async def process_webhook(
        self,
        provider:  PaymentProvider,
        headers:   dict,
        body:      dict,
        raw_body:  str,
    ) -> WebhookLog:
        """
        Log raw inbound webhook payload and attempt to reconcile with a transaction.
        Always logs regardless of outcome — the webhook_logs table is the audit trail.
        """
        provider_ref = (
            body.get("transactionId")
            or body.get("order_id")
            or body.get("output_ConversationID")
            or body.get("reference")
        )

        txn_id = None
        if provider_ref:
            txn = await self.repo.find_transaction_by_provider_ref(provider_ref)
            if txn:
                txn_id = txn.id

        wh = WebhookLog(
            provider       = provider,
            headers        = headers,
            body           = body,
            raw_body       = raw_body,
            transaction_id = txn_id,
        )
        wh = await self.repo.create_webhook_log(wh)

        if txn_id:
            try:
                await self.verify(txn_id)
                wh.processed = True
            except Exception as exc:
                wh.process_error = str(exc)
                log.error("payment.webhook.reconcile_failed",
                          txn_id=str(txn_id), error=str(exc))

        await self.repo.save_webhook_log(wh)
        await self.db.commit()
        return wh

    # ── Refund ────────────────────────────────────────────────────────────────

    async def refund(self, payment_id: uuid.UUID) -> PaymentTransaction:
        payment = await self._get_payment_or_404(payment_id)
        if payment.status != PaymentStatus.PAID:
            raise ValidationError("Only PAID payments can be refunded.")

        txn = await self.repo.get_successful_transaction(payment_id)
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
        refund_txn = await self.repo.create_transaction(refund_txn)
        payment.status = PaymentStatus.REFUNDED
        await self.repo.save_payment(payment)
        await self.db.commit()

        if self.producer:
            try:
                await self.producer.payment_refunded(payment_id, payment.amount)
            except Exception as e:
                log.error("payment.publish_failed", error=str(e))

        return refund_txn

    # ── Cancel ────────────────────────────────────────────────────────────────

    async def cancel(self, payment_id: uuid.UUID) -> Payment:
        payment = await self._get_payment_or_404(payment_id)
        if payment.status != PaymentStatus.PENDING:
            raise ValidationError(
                f"Only PENDING payments can be cancelled. Current: {payment.status.value}"
            )
        payment.status = PaymentStatus.CANCELLED
        await self.repo.save_payment(payment)
        await self.db.commit()
        return payment

    # ── Queries ───────────────────────────────────────────────────────────────

    async def get_payment(self, payment_id: uuid.UUID) -> Payment:
        return await self._get_payment_or_404(payment_id)

    async def list_payments(self, **filters) -> list[Payment]:
        return await self.repo.list_payments(**filters)

    async def get_transaction(self, txn_id: uuid.UUID) -> PaymentTransaction:
        return await self._get_transaction_or_404(txn_id)

    async def list_transactions(self, payment_id: uuid.UUID) -> list[PaymentTransaction]:
        return await self.repo.list_transactions(payment_id)

    async def get_latest_transaction(self, payment_id: uuid.UUID) -> Optional[PaymentTransaction]:
        return await self.repo.get_latest_transaction(payment_id)

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _get_payment_or_404(self, payment_id: uuid.UUID) -> Payment:
        payment = await self.repo.get_payment(payment_id)
        if not payment:
            raise PaymentNotFoundError()
        return payment

    async def _get_transaction_or_404(self, txn_id: uuid.UUID) -> PaymentTransaction:
        txn = await self.repo.get_transaction(txn_id)
        if not txn:
            raise TransactionNotFoundError()
        return txn

"""
repositories/payment_repository.py
────────────────────────────────────────────────────────────────────────────
All database operations for Payment, PaymentTransaction, and WebhookLog.
No business logic — pure query construction and DB I/O.
"""
from __future__ import annotations

import uuid
from typing import Optional

from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.payment import (
    Payment,
    PaymentProvider,
    PaymentStatus,
    PaymentTransaction,
    TransactionStatus,
    WebhookLog,
)


class PaymentRepository:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Payment ───────────────────────────────────────────────────────────────

    async def create_payment(self, payment: Payment) -> Payment:
        self.db.add(payment)
        await self.db.flush()
        await self.db.refresh(payment)
        return payment

    async def get_payment(self, payment_id: uuid.UUID) -> Optional[Payment]:
        result = await self.db.execute(
            select(Payment).where(Payment.id == payment_id)
        )
        return result.scalar_one_or_none()

    async def list_payments(
        self,
        payer_user_id: Optional[uuid.UUID] = None,
        org_id:        Optional[uuid.UUID] = None,
        project_id:    Optional[uuid.UUID] = None,
        reference_id:  Optional[uuid.UUID] = None,
        status:        Optional[str]       = None,
        payment_type:  Optional[str]       = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Payment]:
        q = select(Payment)
        if payer_user_id: q = q.where(Payment.payer_user_id == payer_user_id)
        if org_id:        q = q.where(Payment.org_id        == org_id)
        if project_id:    q = q.where(Payment.project_id    == project_id)
        if reference_id:  q = q.where(Payment.reference_id  == reference_id)
        if status:        q = q.where(Payment.status        == status)
        if payment_type:  q = q.where(Payment.payment_type  == payment_type)
        q = q.order_by(Payment.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def save_payment(self, payment: Payment) -> None:
        self.db.add(payment)

    # ── Transaction ───────────────────────────────────────────────────────────

    async def create_transaction(
        self, txn: PaymentTransaction
    ) -> PaymentTransaction:
        self.db.add(txn)
        await self.db.flush()
        await self.db.refresh(txn)
        return txn

    async def get_transaction(
        self, txn_id: uuid.UUID
    ) -> Optional[PaymentTransaction]:
        result = await self.db.execute(
            select(PaymentTransaction).where(PaymentTransaction.id == txn_id)
        )
        return result.scalar_one_or_none()

    async def get_latest_transaction(
        self, payment_id: uuid.UUID
    ) -> Optional[PaymentTransaction]:
        result = await self.db.execute(
            select(PaymentTransaction)
            .where(PaymentTransaction.payment_id == payment_id)
            .order_by(PaymentTransaction.initiated_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_successful_transaction(
        self, payment_id: uuid.UUID
    ) -> Optional[PaymentTransaction]:
        result = await self.db.execute(
            select(PaymentTransaction).where(
                PaymentTransaction.payment_id == payment_id,
                PaymentTransaction.status     == TransactionStatus.SUCCESS,
            )
        )
        return result.scalar_one_or_none()

    async def list_transactions(
        self, payment_id: uuid.UUID
    ) -> list[PaymentTransaction]:
        result = await self.db.execute(
            select(PaymentTransaction)
            .where(PaymentTransaction.payment_id == payment_id)
            .order_by(PaymentTransaction.initiated_at)
        )
        return list(result.scalars().all())

    async def find_transaction_by_provider_ref(
        self, provider_ref: str
    ) -> Optional[PaymentTransaction]:
        result = await self.db.execute(
            select(PaymentTransaction).where(
                PaymentTransaction.provider_ref == provider_ref
            )
        )
        return result.scalar_one_or_none()

    async def save_transaction(self, txn: PaymentTransaction) -> None:
        self.db.add(txn)

    # ── Webhook log ───────────────────────────────────────────────────────────

    async def create_webhook_log(self, wh: WebhookLog) -> WebhookLog:
        self.db.add(wh)
        await self.db.flush()
        await self.db.refresh(wh)
        return wh

    async def save_webhook_log(self, wh: WebhookLog) -> None:
        self.db.add(wh)

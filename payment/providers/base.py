"""
providers/base.py
────────────────────────────────────────────────────────────────────────────
Abstract base class for all payment providers.
Each provider implements: initiate, verify, refund.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

from models.payment import Payment, PaymentProvider, PaymentTransaction


class BasePaymentProvider(ABC):
    name: PaymentProvider

    @abstractmethod
    async def initiate(self, payment: Payment, phone: str) -> Dict[str, Any]:
        """
        Send payment request to the provider.
        Returns dict with at least: provider_ref, status.
        May include checkout_url for redirect flows.
        """
        ...

    @abstractmethod
    async def verify(self, provider_ref: str) -> Dict[str, Any]:
        """Check status of a previously initiated payment."""
        ...

    @abstractmethod
    async def refund(self, transaction: PaymentTransaction) -> Dict[str, Any]:
        """Initiate a refund for a completed transaction."""
        ...

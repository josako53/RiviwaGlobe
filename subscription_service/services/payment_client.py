"""services/payment_client.py — HTTP client to payment_service.

subscription_service delegates all payment gateway calls to payment_service
so we don't duplicate gateway code. This client wraps the payment_service API.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

import httpx
import structlog

from core.config import settings

log = structlog.get_logger(__name__)

_BASE = "http://payment_service:8040/api/v1"
_HEADERS = {"X-Service-Key": settings.INTERNAL_SERVICE_KEY}

USD_TO_TZS = Decimal("2600")


async def create_payment(
    org_id:        str,
    amount_usd:    Decimal,
    invoice_id:    str,
    invoice_number: str,
    payer_phone:   Optional[str] = None,
    payer_email:   Optional[str] = None,
    payer_name:    Optional[str] = None,
    internal_token: Optional[str] = None,
) -> dict:
    """Create a payment intent in payment_service. Returns payment dict."""
    # payment_service works in TZS by default — convert USD
    amount_tzs = float(amount_usd * USD_TO_TZS)

    headers = {}
    if internal_token:
        headers["Authorization"] = f"Bearer {internal_token}"

    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            f"{_BASE}/payments",
            headers=headers,
            json={
                "payment_type":   "subscription",
                "amount":         amount_tzs,
                "currency":       "TZS",
                "phone":          payer_phone or "",
                "payer_email":    payer_email,
                "payer_name":     payer_name,
                "org_id":         org_id,
                "reference_id":   invoice_id,
                "reference_type": "invoice",
                "description":    f"Riviwa subscription — {invoice_number}",
            },
        )
    r.raise_for_status()
    return r.json()


async def initiate_payment(
    payment_id:    str,
    provider:      str,
    internal_token: Optional[str] = None,
) -> dict:
    """Initiate a payment with the given provider. Returns transaction dict with checkout_url."""
    headers = {}
    if internal_token:
        headers["Authorization"] = f"Bearer {internal_token}"
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{_BASE}/payments/{payment_id}/initiate",
            headers=headers,
            json={"provider": provider},
        )
    r.raise_for_status()
    return r.json()


async def get_payment_status(payment_id: str, internal_token: Optional[str] = None) -> dict:
    headers = {}
    if internal_token:
        headers["Authorization"] = f"Bearer {internal_token}"
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{_BASE}/payments/{payment_id}", headers=headers)
    r.raise_for_status()
    return r.json()

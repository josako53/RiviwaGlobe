"""
providers/azampay.py — AzamPay provider
────────────────────────────────────────────────────────────────────────────
AzamPay checkout API (Tanzania).
Supports: Airtel Money TZ, M-Pesa (via AzamPay routing), CRDB, NMB.

Docs: https://developers.azampay.co.tz/

Flow:
  1. POST /authenticator/oauth/token      → bearer token
  2. POST /merchant/v1/mobile-checkout    → initiate USSD push
  3. Callback POST /webhooks/azampay      → status update
  4. GET  /merchant/v1/transaction/status → verify
"""
from __future__ import annotations

import uuid
from typing import Any, Dict

import httpx

from core.config import settings
from core.exceptions import PaymentProviderError
from models.payment import Payment, PaymentProvider, PaymentTransaction
from providers.base import BasePaymentProvider


def _network(phone: str) -> str:
    """Map Tanzanian phone prefix to AzamPay network string."""
    digits = phone.lstrip("+")
    prefix = digits[3:5] if digits.startswith("255") and len(digits) >= 6 else digits[:2]
    mapping = {
        "74": "Airtel", "75": "Airtel", "78": "Airtel",
        "71": "Tigo",   "65": "Tigo",   "67": "Tigo",
        "76": "Halotel", "77": "Halotel",
        "68": "TTCL",    "69": "TTCL",
        "61": "Vodacom", "62": "Vodacom", "73": "Vodacom",
    }
    return mapping.get(prefix, "Airtel")


class AzamPayProvider(BasePaymentProvider):
    name = PaymentProvider.AZAMPAY

    async def _get_token(self) -> str:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{settings.AZAMPAY_BASE_URL}/authenticator/oauth/token",
                json={
                    "appName":      settings.AZAMPAY_APP_NAME,
                    "clientId":     settings.AZAMPAY_CLIENT_ID,
                    "clientSecret": settings.AZAMPAY_CLIENT_SECRET,
                },
            )
            if resp.status_code != 200:
                raise PaymentProviderError(
                    "azampay", f"Auth failed: {resp.status_code} {resp.text[:200]}"
                )
            return resp.json()["data"]["accessToken"]

    async def initiate(self, payment: Payment, phone: str) -> Dict[str, Any]:
        token      = await self._get_token()
        amount_str = str(int(payment.amount))
        external_id = payment.external_ref or str(uuid.uuid4())

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{settings.AZAMPAY_CHECKOUT_URL}/azampay/merchant/v1/mobile-checkout",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "accountNumber": phone,
                    "amount":        amount_str,
                    "currency":      payment.currency.value,
                    "externalId":    external_id,
                    "provider":      _network(phone),
                    "additionalProperties": {
                        "description": payment.description or "Riviwa payment",
                    },
                },
            )
        data = resp.json()
        if resp.status_code not in (200, 201):
            raise PaymentProviderError("azampay", data.get("message", resp.text[:200]))

        return {
            "provider_ref":    data.get("transactionId", external_id),
            "provider_order_id": external_id,
            "status":          "pending",
            "provider_response": data,
        }

    async def verify(self, provider_ref: str) -> Dict[str, Any]:
        token = await self._get_token()
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{settings.AZAMPAY_CHECKOUT_URL}/azampay/merchant/v1/transaction/status",
                headers={"Authorization": f"Bearer {token}"},
                params={"pgReferenceId": provider_ref},
            )
        data       = resp.json()
        raw_status = str(data.get("paymentStatus", "")).lower()
        mapping    = {"success": "success", "completed": "success",
                      "failed": "failed", "cancelled": "failed"}
        status = mapping.get(raw_status, "pending")
        return {"status": status, "provider_response": data}

    async def refund(self, transaction: PaymentTransaction) -> Dict[str, Any]:
        raise PaymentProviderError(
            "azampay",
            "Automated refunds are not supported. Use the AzamPay merchant portal.",
        )

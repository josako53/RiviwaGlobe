"""providers/paypal.py — PayPal REST API v2 payment provider."""
from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

import httpx
import structlog

from core.config import settings
from core.exceptions import PaymentProviderError
from models.payment import Payment, PaymentProvider, PaymentTransaction
from providers import BasePaymentProvider

log = structlog.get_logger(__name__)

PAYPAL_LIVE    = "https://api.paypal.com"
PAYPAL_SANDBOX = "https://api.sandbox.paypal.com"


class PayPalProvider(BasePaymentProvider):
    """
    PayPal REST API v2 — Orders + Capture.

    Flow:
      1. POST /v2/checkout/orders → create order, get approve_url
      2. Redirect user to approve_url (PayPal hosted page)
      3. User approves → PayPal calls return_url with ?token=ORDER_ID
      4. POST /v2/checkout/orders/{order_id}/capture → capture funds
      5. Webhook: PAYMENT.CAPTURE.COMPLETED → confirm settlement

    Supports: Visa, Mastercard, PayPal balance, bank accounts.
    Currency: USD (default), EUR, GBP and more.

    Credentials: PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET, PAYPAL_SANDBOX.
    """
    name = PaymentProvider.PAYPAL

    def _base_url(self) -> str:
        return PAYPAL_SANDBOX if settings.PAYPAL_SANDBOX else PAYPAL_LIVE

    async def _token(self) -> str:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                f"{self._base_url()}/v1/oauth2/token",
                auth=(settings.PAYPAL_CLIENT_ID, settings.PAYPAL_CLIENT_SECRET),
                data={"grant_type": "client_credentials"},
                headers={"Accept": "application/json"},
            )
            if r.status_code != 200:
                raise PaymentProviderError("paypal", f"Auth failed: {r.text[:200]}")
            return r.json()["access_token"]

    async def initiate(self, payment: Payment, phone: str) -> Dict[str, Any]:
        token = await self._token()
        reference_id = payment.external_ref or f"RVW-{uuid.uuid4().hex[:12].upper()}"

        # Convert TZS to USD if needed (payment amounts may be in TZS)
        currency = "USD"
        amount   = payment.amount
        if hasattr(payment, "currency") and payment.currency and payment.currency.value != "USD":
            # Use TZS→USD approximate rate
            amount = round(payment.amount / 2600, 2)

        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{self._base_url()}/v2/checkout/orders",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "PayPal-Request-Id": reference_id,
                },
                json={
                    "intent": "CAPTURE",
                    "purchase_units": [{
                        "reference_id": reference_id,
                        "description":  payment.description or "Riviwa subscription",
                        "amount": {
                            "currency_code": currency,
                            "value": f"{amount:.2f}",
                        },
                    }],
                    "payment_source": {
                        "paypal": {
                            "experience_context": {
                                "payment_method_preference": "IMMEDIATE_PAYMENT_REQUIRED",
                                "brand_name":    "Riviwa",
                                "locale":        "en-US",
                                "landing_page":  "LOGIN",
                                "user_action":   "PAY_NOW",
                                "return_url":    f"{settings.PAYMENT_CALLBACK_BASE_URL}/api/v1/webhooks/paypal/return",
                                "cancel_url":    f"{settings.PAYMENT_CALLBACK_BASE_URL}/api/v1/webhooks/paypal/cancel",
                            }
                        }
                    },
                },
            )

        data = r.json()
        if r.status_code not in (200, 201):
            raise PaymentProviderError("paypal", data.get("message", r.text[:300]))

        order_id    = data.get("id")
        approve_url = next(
            (link["href"] for link in data.get("links", []) if link["rel"] == "payer-action"),
            None,
        )

        log.info("paypal.order_created", order_id=order_id, reference_id=reference_id)
        return {
            "provider_ref":      order_id,
            "provider_order_id": reference_id,
            "checkout_url":      approve_url,
            "status":            "pending",
            "provider_response": data,
        }

    async def capture(self, order_id: str) -> Dict[str, Any]:
        token = await self._token()
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{self._base_url()}/v2/checkout/orders/{order_id}/capture",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
        data = r.json()
        success = data.get("status") in ("COMPLETED", "APPROVED")
        return {
            "status":            "success" if success else "failed",
            "provider_response": data,
            "receipt":           data.get("id"),
        }

    async def verify(self, provider_ref: str) -> Dict[str, Any]:
        """Check order status (used for polling)."""
        token = await self._token()
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"{self._base_url()}/v2/checkout/orders/{provider_ref}",
                headers={"Authorization": f"Bearer {token}"},
            )
        data = r.json()
        raw_status = data.get("status", "").upper()
        status_map = {
            "COMPLETED": "success",
            "APPROVED":  "success",
            "VOIDED":    "failed",
            "CREATED":   "pending",
            "SAVED":     "pending",
        }
        return {
            "status":            status_map.get(raw_status, "pending"),
            "provider_response": data,
        }

    async def refund(self, transaction: PaymentTransaction) -> Dict[str, Any]:
        """Refund a captured PayPal payment."""
        token = await self._token()
        capture_id = (transaction.provider_response or {}).get("purchase_units", [{}])[0] \
                         .get("payments", {}).get("captures", [{}])[0].get("id")
        if not capture_id:
            raise PaymentProviderError("paypal", "Capture ID not found in transaction response.")

        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{self._base_url()}/v2/payments/captures/{capture_id}/refund",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={},
            )
        data = r.json()
        success = data.get("status") in ("COMPLETED", "PENDING")
        return {"status": "success" if success else "failed", "provider_response": data}

    async def verify_webhook(self, headers: dict, body: bytes, webhook_id: str) -> bool:
        """Verify PayPal webhook signature."""
        if not settings.PAYPAL_WEBHOOK_ID:
            return True  # Skip verification if not configured
        token = await self._token()
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                f"{self._base_url()}/v1/notifications/verify-webhook-signature",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={
                    "auth_algo":          headers.get("paypal-auth-algo", ""),
                    "cert_url":           headers.get("paypal-cert-url", ""),
                    "transmission_id":    headers.get("paypal-transmission-id", ""),
                    "transmission_sig":   headers.get("paypal-transmission-sig", ""),
                    "transmission_time":  headers.get("paypal-transmission-time", ""),
                    "webhook_id":         webhook_id,
                    "webhook_event":      body.decode(),
                },
            )
        return r.json().get("verification_status") == "SUCCESS"

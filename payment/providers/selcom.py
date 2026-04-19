"""
providers/selcom.py — Selcom Payment Gateway provider
────────────────────────────────────────────────────────────────────────────
Selcom Payment Gateway (Tanzania).
Supports: Tigo Pesa, TTCL Pesa, Halotel.

Docs: https://developer.selcom.co.tz/

Flow:
  1. POST /checkout/create-order     → get order_id + payment_token
  2. Customer pays via USSD or Selcom app (optional checkout_url redirect)
  3. Callback POST /webhooks/selcom  → order status update
  4. POST /checkout/order-status     → verify

Every request is signed with HMAC-SHA256.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

import httpx

from core.config import settings
from core.exceptions import PaymentProviderError
from models.payment import Payment, PaymentProvider, PaymentTransaction
from providers.base import BasePaymentProvider


class SelcomProvider(BasePaymentProvider):
    name = PaymentProvider.SELCOM

    def _sign(self, body: str, timestamp: str) -> str:
        msg = timestamp + settings.SELCOM_API_KEY + body
        return hmac.new(
            settings.SELCOM_API_SECRET.encode(),
            msg.encode(),
            hashlib.sha256,
        ).hexdigest()

    def _headers(self, body_str: str) -> Dict[str, str]:
        ts  = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S%z")
        dig = base64.b64encode(hashlib.sha256(body_str.encode()).digest()).decode()
        return {
            "Content-Type":  "application/json;charset=utf-8",
            "Accept":        "application/json",
            "Authorization": f"SELCOM {settings.SELCOM_API_KEY}",
            "Digest":        f"SHA-256={dig}",
            "Timestamp":     ts,
            "Signed-Fields": "timestamp,authorization,digest",
            "Signature":     self._sign(body_str, ts),
        }

    async def initiate(self, payment: Payment, phone: str) -> Dict[str, Any]:
        order_id  = payment.external_ref or f"RVW-{uuid.uuid4().hex[:12].upper()}"
        fname     = (payment.payer_name or "Consumer").split()[0]
        lname     = (payment.payer_name or "Consumer").split()[-1]
        body_dict = {
            "vendor":          settings.SELCOM_VENDOR,
            "order_id":        order_id,
            "buyer_email":     payment.payer_email or "",
            "buyer_name":      payment.payer_name or "Consumer",
            "buyer_phone":     phone,
            "amount":          int(payment.amount),
            "currency":        payment.currency.value,
            "payment_methods": "MASTERCARD,VISA,AIRTELMONEY,TIGOPESA",
            "redirect_url":    f"{settings.PAYMENT_CALLBACK_BASE_URL}/payment/redirect",
            "cancel_url":      f"{settings.PAYMENT_CALLBACK_BASE_URL}/payment/cancel",
            "webhook":         f"{settings.PAYMENT_CALLBACK_BASE_URL}/api/v1/webhooks/selcom",
            "header_colour":   "#0C447C",
            "billing.firstname": fname,
            "billing.lastname":  lname,
            "billing.address_1": "Dar es Salaam",
            "billing.city":      "Dar es Salaam",
            "billing.country":   "TZ",
            "billing.phone":     phone,
        }
        body_str = json.dumps(body_dict)
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{settings.SELCOM_BASE_URL}/checkout/create-order",
                headers=self._headers(body_str),
                content=body_str,
            )
        data = resp.json()
        if data.get("resultcode") != "000":
            raise PaymentProviderError("selcom", data.get("result", resp.text[:200]))

        payment_url = data.get("data", [{}])[0].get("payment_gateway_url", "")
        return {
            "provider_ref":    order_id,
            "provider_order_id": order_id,
            "checkout_url":    payment_url,
            "status":          "pending",
            "provider_response": data,
        }

    async def verify(self, provider_ref: str) -> Dict[str, Any]:
        body_dict = {"vendor": settings.SELCOM_VENDOR, "order_id": provider_ref}
        body_str  = json.dumps(body_dict)
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{settings.SELCOM_BASE_URL}/checkout/order-status",
                headers=self._headers(body_str),
                content=body_str,
            )
        data       = resp.json()
        raw_status = str((data.get("data") or [{}])[0].get("payment_status", "")).lower()
        mapping    = {"complete": "success", "paid": "success",
                      "canceled": "failed", "failed": "failed"}
        status = mapping.get(raw_status, "pending")
        return {"status": status, "provider_response": data}

    async def refund(self, transaction: PaymentTransaction) -> Dict[str, Any]:
        raise PaymentProviderError(
            "selcom",
            "Automated refunds are not supported. Use the Selcom merchant portal.",
        )

"""providers/yas.py — Yas Money Tanzania (formerly Tigo Pesa).

Yas is the rebranded Tigo Tanzania telecom — Tigo Pesa became Yas Money in 2023.

API: Yas Money REST API — OAuth2 + USSD Push
Base URLs:
  Staging:    https://api.sandbox.yasmoney.co.tz
  Production: https://api.yasmoney.co.tz

Flow:
  1. POST /v1/oauth/token → Bearer token
  2. POST /v1/c2b/payment → initiate USSD push (C2B collection)
     Consumer receives USSD prompt on their phone
  3. GET  /v1/c2b/payment/{reference} → transaction status
  4. POST /webhooks/yas → Yas sends callback on final status
  5. POST /v1/c2b/refund → refund

Status values (Yas Money):
  SUCCESS    — Payment completed
  PENDING    — Awaiting consumer action
  FAILED     — Payment failed
  CANCELLED  — Consumer cancelled
  EXPIRED    — Session timed out

Note: Phone number without country code (e.g. 71234567, not +25571234567).
Credentials: AIRTEL_CLIENT_ID / AIRTEL_CLIENT_SECRET apply to Airtel.
             YAS_CLIENT_ID / YAS_CLIENT_SECRET apply to Yas Money.

Obtain from: https://developer.yasmoney.co.tz (or Yas Money partner portal)
"""
from __future__ import annotations

import base64
import time
from typing import Any, Dict, Optional

import httpx
import structlog

from core.config import settings
from core.exceptions import PaymentProviderError
from models.payment import Payment, PaymentProvider, PaymentTransaction
from providers import BasePaymentProvider

log = structlog.get_logger(__name__)

_YAS_STATUS_MAP = {
    "SUCCESS":   "success",
    "COMPLETED": "success",
    "FAILED":    "failed",
    "CANCELLED": "failed",
    "EXPIRED":   "failed",
    "PENDING":   "pending",
    "PROCESSING": "pending",
}

_token_cache: dict = {"token": None, "expires_at": 0.0}


class YasMoneyProvider(BasePaymentProvider):
    """
    Yas Money Tanzania (formerly Tigo Pesa) — C2B collection via USSD push.

    Configuration (set via environment variables):
      YAS_CLIENT_ID        — OAuth2 client ID from Yas partner portal
      YAS_CLIENT_SECRET    — OAuth2 client secret
      YAS_MERCHANT_CODE    — Merchant code assigned by Yas
      YAS_SANDBOX          — "true" for staging, "false" for production
    """
    name = PaymentProvider.YAS

    def _base_url(self) -> str:
        return (
            "https://api.sandbox.yasmoney.co.tz"
            if settings.YAS_SANDBOX
            else "https://api.yasmoney.co.tz"
        )

    async def _get_token(self) -> str:
        global _token_cache
        if _token_cache["token"] and time.time() < _token_cache["expires_at"]:
            return _token_cache["token"]

        creds = base64.b64encode(
            f"{settings.YAS_CLIENT_ID}:{settings.YAS_CLIENT_SECRET}".encode()
        ).decode()

        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                f"{self._base_url()}/v1/oauth/token",
                headers={
                    "Authorization": f"Basic {creds}",
                    "Content-Type":  "application/x-www-form-urlencoded",
                },
                data={"grant_type": "client_credentials"},
            )

        if r.status_code != 200:
            raise PaymentProviderError("yas", f"OAuth2 token error: {r.text[:200]}")

        data  = r.json()
        token = data.get("access_token")
        if not token:
            raise PaymentProviderError("yas", f"No access_token in response: {r.text[:200]}")

        expires_in = int(data.get("expires_in", 3600))
        _token_cache = {"token": token, "expires_at": time.time() + expires_in - 60}
        return token

    def _strip_country_code(self, phone: str) -> str:
        phone = phone.lstrip("+")
        if phone.startswith("255"):
            phone = phone[3:]
        return phone

    async def initiate(self, payment: Payment, phone: str) -> Dict[str, Any]:
        token   = await self._get_token()
        msisdn  = self._strip_country_code(phone)
        ref     = payment.external_ref or f"RVW-{payment.id.hex[:12].upper()}"
        amount  = int(payment.amount)

        body = {
            "merchant_code":  settings.YAS_MERCHANT_CODE,
            "reference":      ref,
            "amount":         amount,
            "currency":       "TZS",
            "msisdn":         msisdn,
            "description":    payment.description or "Riviwa payment",
            "callback_url": (
                f"{settings.PAYMENT_CALLBACK_BASE_URL}/api/v1/webhooks/yas"
            ),
        }

        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{self._base_url()}/v1/c2b/payment",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type":  "application/json",
                    "Accept":        "application/json",
                },
                json=body,
            )

        data = r.json()
        if r.status_code not in (200, 201, 202):
            raise PaymentProviderError(
                "yas",
                data.get("message") or data.get("error") or r.text[:200]
            )

        yas_ref  = data.get("transaction_id") or data.get("reference") or ref
        status   = data.get("status", "PENDING")

        log.info("yas.initiated", ref=ref, msisdn=msisdn[:4] + "****", status=status)
        return {
            "provider_ref":      ref,
            "provider_order_id": yas_ref,
            "checkout_url":      data.get("ussd_push_url"),   # if Yas provides redirect
            "status":            "pending",
            "provider_response": data,
        }

    async def verify(self, provider_ref: str) -> Dict[str, Any]:
        """GET /v1/c2b/payment/{reference} — transaction status enquiry."""
        token = await self._get_token()

        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"{self._base_url()}/v1/c2b/payment/{provider_ref}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept":        "application/json",
                },
            )

        data       = r.json()
        raw_status = (data.get("status") or data.get("transaction_status") or "").upper()
        status     = _YAS_STATUS_MAP.get(raw_status, "pending")
        receipt    = data.get("transaction_id") or data.get("yas_transaction_id")

        log.info("yas.verify", ref=provider_ref, raw_status=raw_status, status=status)
        return {
            "status":            status,
            "receipt":           receipt,
            "provider_response": data,
        }

    async def refund(self, transaction: PaymentTransaction) -> Dict[str, Any]:
        """POST /v1/c2b/refund — full refund by Yas transaction ID."""
        yas_txn_id = (
            (transaction.provider_response or {}).get("transaction_id")
            or transaction.provider_receipt
            or transaction.provider_ref
        )
        if not yas_txn_id:
            raise PaymentProviderError("yas", "Yas transaction ID not found. Cannot refund.")

        token = await self._get_token()
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{self._base_url()}/v1/c2b/refund",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type":  "application/json",
                },
                json={
                    "transaction_id":     yas_txn_id,
                    "merchant_code":      settings.YAS_MERCHANT_CODE,
                    "refund_reference":   f"REF-{transaction.id}",
                },
            )

        data    = r.json()
        success = (data.get("status") or "").upper() in ("SUCCESS", "COMPLETED")
        log.info("yas.refund", yas_txn_id=yas_txn_id, success=success)
        return {
            "status":            "success" if success else "failed",
            "provider_response": data,
        }

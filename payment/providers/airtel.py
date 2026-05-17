"""providers/airtel.py — Airtel Money Tanzania (Collection + Refund + Enquiry).

Docs: https://openapi.airtel.co.tz (production)
      https://openapiuat.airtel.co.tz (staging)

OAuth2 client-credentials flow. Phone without country code (e.g. 75123456, not +25575123456).

Status codes:
  TS  — Transaction Success
  TF  — Transaction Failed
  TA  — Transaction Ambiguous (still processing)
  TIP — Transaction in Progress
  TE  — Transaction Expired

Response codes (key ones):
  DP00800001001 — Success
  DP00800001006 — In process (pending)
  DP00800001002 — Incorrect PIN
  DP00800001007 — Not enough balance
  DP00800001024 — Timed out
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

_AIRTEL_STATUS_MAP = {
    "TS":  "success",
    "TF":  "failed",
    "TE":  "failed",    # expired
    "TA":  "pending",   # ambiguous — retry later
    "TIP": "pending",   # in progress
}

# Module-level token cache
_token_cache: dict = {"token": None, "expires_at": 0.0}


class AirtelMoneyProvider(BasePaymentProvider):
    """
    Airtel Money Tanzania — USSD Push (C2B collection).

    Flow:
      1. POST /auth/oauth2/token → Bearer token (client_credentials)
      2. POST /merchant/v1/payments/ → initiate USSD push
         Consumer sees prompt on phone, enters PIN
      3. GET  /standard/v1/payments/{id} → transaction enquiry (poll)
      4. POST /webhooks/airtel → callback (Airtel sends final status)
      5. POST /standard/v1/payments/refund → refund by airtel_money_id

    Note: msisdn must NOT include country code.
    """
    name = PaymentProvider.AIRTEL

    def _base_url(self) -> str:
        return (
            "https://openapiuat.airtel.co.tz"
            if settings.AIRTEL_SANDBOX
            else "https://openapi.airtel.co.tz"
        )

    async def _get_token(self) -> str:
        global _token_cache
        if _token_cache["token"] and time.time() < _token_cache["expires_at"]:
            return _token_cache["token"]

        creds = base64.b64encode(
            f"{settings.AIRTEL_CLIENT_ID}:{settings.AIRTEL_CLIENT_SECRET}".encode()
        ).decode()

        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                f"{self._base_url()}/auth/oauth2/token",
                headers={
                    "Authorization": f"Basic {creds}",
                    "Content-Type":  "application/x-www-form-urlencoded",
                },
                data={"grant_type": "client_credentials"},
            )
        if r.status_code != 200:
            raise PaymentProviderError("airtel", f"OAuth2 token error: {r.text[:200]}")

        data  = r.json()
        token = data.get("access_token")
        if not token:
            raise PaymentProviderError("airtel", f"No access_token in response: {r.text[:200]}")

        expires_in = int(data.get("expires_in", 3600))
        _token_cache = {"token": token, "expires_at": time.time() + expires_in - 60}
        log.debug("airtel.token_refreshed", expires_in=expires_in)
        return token

    def _strip_country_code(self, phone: str) -> str:
        """Remove +255 or 255 prefix — Airtel wants local format."""
        phone = phone.lstrip("+")
        if phone.startswith("255"):
            phone = phone[3:]
        return phone

    async def initiate(self, payment: Payment, phone: str) -> Dict[str, Any]:
        token   = await self._get_token()
        msisdn  = self._strip_country_code(phone)
        txn_id  = payment.external_ref or f"RVW-{payment.id.hex[:12].upper()}"
        amount  = int(payment.amount)

        body = {
            "reference": payment.description or "Riviwa payment",
            "subscriber": {
                "country":  "TZ",
                "currency": "TZS",
                "msisdn":   msisdn,
            },
            "transaction": {
                "amount":   amount,
                "country":  "TZ",
                "currency": "TZS",
                "id":       txn_id,
            },
        }

        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{self._base_url()}/merchant/v1/payments/",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type":  "application/json",
                    "Accept":        "*/*",
                    "X-Country":     "TZ",
                    "X-Currency":    "TZS",
                },
                json=body,
            )

        data = r.json()
        status_block = data.get("status", {})
        success      = status_block.get("success", False)
        resp_code    = status_block.get("response_code", "")

        # DP00800001006 = "In process" (pending) — treat as success of initiation
        if not success and resp_code not in ("DP00800001006", "DP00800001001"):
            raise PaymentProviderError(
                "airtel",
                f"{status_block.get('message', 'Unknown error')} "
                f"[{resp_code}]"
            )

        txn_data    = data.get("data", {}).get("transaction", {})
        airtel_txn  = txn_data.get("id", txn_id)

        log.info("airtel.initiated", txn_id=txn_id, msisdn=msisdn[:4] + "****",
                 resp_code=resp_code)
        return {
            "provider_ref":      txn_id,        # our ID — used for enquiry
            "provider_order_id": airtel_txn,     # Airtel's ID
            "status":            "pending",
            "provider_response": data,
        }

    async def verify(self, provider_ref: str) -> Dict[str, Any]:
        """GET /standard/v1/payments/{id} — transaction enquiry by our txn ID."""
        token = await self._get_token()

        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"{self._base_url()}/standard/v1/payments/{provider_ref}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept":        "*/*",
                    "X-Country":     "TZ",
                    "X-Currency":    "TZS",
                },
            )

        data       = r.json()
        txn_data   = data.get("data", {}).get("transaction", {})
        raw_status = txn_data.get("status", "")
        status     = _AIRTEL_STATUS_MAP.get(raw_status, "pending")
        receipt    = txn_data.get("airtel_money_id")

        log.info("airtel.verify", provider_ref=provider_ref, raw_status=raw_status, status=status)
        return {
            "status":            status,
            "receipt":           receipt,
            "provider_response": data,
        }

    async def refund(self, transaction: PaymentTransaction) -> Dict[str, Any]:
        """POST /standard/v1/payments/refund — full refund by airtel_money_id."""
        airtel_money_id = (
            (transaction.provider_response or {})
            .get("data", {})
            .get("transaction", {})
            .get("airtel_money_id")
            or transaction.provider_receipt
        )
        if not airtel_money_id:
            raise PaymentProviderError(
                "airtel",
                "airtel_money_id not found in transaction. Cannot refund."
            )

        token = await self._get_token()
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{self._base_url()}/standard/v1/payments/refund",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type":  "application/json",
                    "Accept":        "*/*",
                    "X-Country":     "TZ",
                    "X-Currency":    "TZS",
                },
                json={"transaction": {"airtel_money_id": airtel_money_id}},
            )

        data    = r.json()
        success = data.get("status", {}).get("success", False)
        refund_status = (
            data.get("data", {}).get("transaction", {}).get("status", "")
        )
        ok = success or refund_status == "SUCCESS"

        log.info("airtel.refund", airtel_money_id=airtel_money_id, ok=ok)
        return {
            "status":            "success" if ok else "failed",
            "provider_response": data,
        }

"""
providers/mpesa.py — Vodacom M-Pesa Tanzania provider
────────────────────────────────────────────────────────────────────────────
Vodacom M-Pesa Tanzania Open API (direct integration).

Docs: https://openapiportal.m-pesa.com/

Flow:
  1. Encrypt MPESA_API_KEY with RSA public key → session key (cached 23h)
  2. POST /ipg/v2/vodacomTZN/c2bPayment/singleStage → USSD push to customer
  3. Customer enters PIN on their phone
  4. Callback POST /webhooks/mpesa → confirmation
  5. GET  /ipg/v2/vodacomTZN/queryTransactionStatus → verify

Session keys expire after ~24 hours; we cache for 23 to be safe.
"""
from __future__ import annotations

import base64
import time
import uuid
from typing import Any, Dict, Optional

import httpx

from core.config import settings
from core.exceptions import PaymentProviderError
from models.payment import Payment, PaymentProvider, PaymentTransaction
from providers.base import BasePaymentProvider


class MpesaProvider(BasePaymentProvider):
    name = PaymentProvider.MPESA

    # Class-level session key cache (shared across instances)
    _session_key: Optional[str] = None
    _session_key_ts: float = 0.0

    async def _get_session_key(self) -> str:
        """Encrypt MPESA_API_KEY with RSA public key to obtain session key."""
        if self._session_key and (time.time() - self._session_key_ts) < 82800:
            return self._session_key

        try:
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.asymmetric import padding

            pub_key_bytes = base64.b64decode(settings.MPESA_PUBLIC_KEY)
            pub_key       = serialization.load_der_public_key(pub_key_bytes)
            encrypted     = pub_key.encrypt(
                settings.MPESA_API_KEY.encode(),
                padding.PKCS1v15(),
            )
            MpesaProvider._session_key    = base64.b64encode(encrypted).decode()
            MpesaProvider._session_key_ts = time.time()
            return MpesaProvider._session_key

        except ImportError:
            raise PaymentProviderError(
                "mpesa",
                "cryptography package is required for M-Pesa. "
                "Install with: pip install cryptography",
            )

    async def initiate(self, payment: Payment, phone: str) -> Dict[str, Any]:
        session_key     = await self._get_session_key()
        msisdn          = phone.lstrip("+")
        third_party_ref = payment.external_ref or f"RVW{uuid.uuid4().hex[:10].upper()}"

        async with httpx.AsyncClient(
            timeout=30,
            headers={
                "Authorization": f"Bearer {session_key}",
                "Origin":        settings.PAYMENT_CALLBACK_BASE_URL,
            },
        ) as client:
            resp = await client.post(
                f"{settings.MPESA_BASE_URL}/ipg/v2/vodacomTZN/c2bPayment/singleStage/",
                json={
                    "input_Amount":                str(int(payment.amount)),
                    "input_Country":               "TZN",
                    "input_Currency":              "TZS",
                    "input_CustomerMSISDN":        msisdn,
                    "input_ServiceProviderCode":   settings.MPESA_SERVICE_PROVIDER_CODE,
                    "input_ThirdPartyConversationID": third_party_ref,
                    "input_TransactionReference":  third_party_ref,
                    "input_PurchasedItemsDesc":    payment.description or "Riviwa",
                },
            )
        data = resp.json()
        if data.get("output_ResponseCode") not in ("INS-0", "INS-I"):
            raise PaymentProviderError(
                "mpesa", data.get("output_ResponseDesc", resp.text[:200])
            )

        conv_id = data.get("output_ConversationID", third_party_ref)
        return {
            "provider_ref":      conv_id,
            "provider_order_id": third_party_ref,
            "status":            "pending",
            "provider_response": data,
        }

    async def verify(self, provider_ref: str) -> Dict[str, Any]:
        session_key     = await self._get_session_key()
        third_party_ref = f"QRY{uuid.uuid4().hex[:8].upper()}"

        async with httpx.AsyncClient(
            timeout=15,
            headers={
                "Authorization": f"Bearer {session_key}",
                "Origin":        settings.PAYMENT_CALLBACK_BASE_URL,
            },
        ) as client:
            resp = await client.get(
                f"{settings.MPESA_BASE_URL}/ipg/v2/vodacomTZN/queryTransactionStatus/",
                params={
                    "input_QueryReference":          provider_ref,
                    "input_ServiceProviderCode":     settings.MPESA_SERVICE_PROVIDER_CODE,
                    "input_ThirdPartyConversationID": third_party_ref,
                    "input_Country":                 "TZN",
                },
            )
        data   = resp.json()
        status = "success" if data.get("output_ResponseCode") == "INS-0" else "failed"
        return {"status": status, "provider_response": data}

    async def refund(self, transaction: PaymentTransaction) -> Dict[str, Any]:
        raise PaymentProviderError(
            "mpesa",
            "Automated refunds are not supported via API. Use the M-Pesa merchant portal.",
        )

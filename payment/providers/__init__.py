"""
providers/base.py + AzamPay + Selcom + M-Pesa
═══════════════════════════════════════════════════════════════════════════════
Each provider implements:
  initiate(payment, phone) → {"provider_ref": str, "checkout_url": str|None, ...}
  verify(provider_ref)     → {"status": "success"|"failed"|"pending", ...}
  refund(transaction)      → {"status": "success"|"failed", ...}

All providers are async and raise PaymentProviderError on failure.
Providers never commit to DB — the service layer owns commits.
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx
import structlog

from core.config import settings
from core.exceptions import PaymentProviderError
from models.payment import Payment, PaymentProvider, PaymentTransaction

log = structlog.get_logger(__name__)


class BasePaymentProvider(ABC):
    name: PaymentProvider

    @abstractmethod
    async def initiate(
        self, payment: Payment, phone: str
    ) -> Dict[str, Any]:
        """
        Initiate a payment request with the provider.
        Returns a dict with at least: provider_ref, status.
        May include checkout_url for redirect flows.
        """
        ...

    @abstractmethod
    async def verify(self, provider_ref: str) -> Dict[str, Any]:
        """Check the status of a previously initiated payment."""
        ...

    @abstractmethod
    async def refund(self, transaction: PaymentTransaction) -> Dict[str, Any]:
        """Initiate a refund for a completed transaction."""
        ...


# ─────────────────────────────────────────────────────────────────────────────
# AzamPay
# ─────────────────────────────────────────────────────────────────────────────

class AzamPayProvider(BasePaymentProvider):
    """
    AzamPay checkout API (Tanzania).
    Supports: Airtel Money TZ, CRDB, NMB, M-Pesa (via AzamPay routing).

    Docs: https://developers.azampay.co.tz/

    Flow:
      1. POST /azampay/authenticator/oauth/token → bearer token
      2. POST /azampay/merchant/v1/mobile-checkout → initiate push USSD
      3. Callback POST /webhooks/azampay → status update
      4. GET  /azampay/merchant/v1/transaction/status → verify

    Mobile USSD push: customer receives STK push on their phone,
    enters PIN to authorise.
    """
    name = PaymentProvider.AZAMPAY

    async def _get_token(self) -> str:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{settings.AZAMPAY_BASE_URL}/authenticator/oauth/token",
                json={
                    "appName":     settings.AZAMPAY_APP_NAME,
                    "clientId":    settings.AZAMPAY_CLIENT_ID,
                    "clientSecret": settings.AZAMPAY_CLIENT_SECRET,
                },
            )
            if resp.status_code != 200:
                raise PaymentProviderError(
                    "azampay",
                    f"Auth failed: {resp.status_code} {resp.text[:200]}"
                )
            return resp.json()["data"]["accessToken"]

    async def initiate(self, payment: Payment, phone: str) -> Dict[str, Any]:
        token = await self._get_token()
        # AzamPay expects amount as integer string
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
                    "provider":      _azampay_network(phone),
                    "additionalProperties": {
                        "description": payment.description or "Riviwa payment",
                    },
                },
            )
        data = resp.json()
        if resp.status_code not in (200, 201):
            raise PaymentProviderError("azampay", data.get("message", resp.text[:200]))

        log.info("azampay.initiated", external_id=external_id, phone=phone[:6]+"****")
        return {
            "provider_ref":   data.get("transactionId", external_id),
            "provider_order_id": external_id,
            "status":         "pending",
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
        data = resp.json()
        raw_status = str(data.get("paymentStatus", "")).lower()
        status = _normalise_status(raw_status, {
            "success": "success", "completed": "success",
            "failed": "failed", "cancelled": "failed",
        })
        return {"status": status, "provider_response": data}

    async def refund(self, transaction: PaymentTransaction) -> Dict[str, Any]:
        # AzamPay refund is a manual process via their portal for now
        raise PaymentProviderError("azampay", "Automated refunds not supported. Use AzamPay portal.")


# ─────────────────────────────────────────────────────────────────────────────
# Selcom
# ─────────────────────────────────────────────────────────────────────────────

class SelcomProvider(BasePaymentProvider):
    """
    Selcom Payment Gateway (Tanzania).
    Supports: Tigo Pesa, TTCL Pesa, Halotel.

    Docs: https://developer.selcom.co.tz/

    Flow:
      1. POST /checkout/create-order → get order_id + payment_token
      2. Customer pays via USSD or Selcom app
      3. Callback POST /webhooks/selcom → order status
      4. POST /checkout/order-status → verify

    HMAC-SHA256 signature on every request.
    """
    name = PaymentProvider.SELCOM

    def _sign(self, body: str, timestamp: str) -> str:
        msg = timestamp + settings.SELCOM_API_KEY + body
        return hmac.new(
            settings.SELCOM_API_SECRET.encode(),
            msg.encode(),
            hashlib.sha256,
        ).hexdigest()

    def _headers(self, body_str: str) -> Dict[str, str]:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S%z")
        return {
            "Content-Type": "application/json;charset=utf-8",
            "Accept":       "application/json",
            "Authorization": f"SELCOM {settings.SELCOM_API_KEY}",
            "Digest":       "SHA-256=" + base64.b64encode(
                hashlib.sha256(body_str.encode()).digest()
            ).decode(),
            "Timestamp":    ts,
            "Signed-Fields": "timestamp,authorization,digest",
            "Signature":    self._sign(body_str, ts),
        }

    async def initiate(self, payment: Payment, phone: str) -> Dict[str, Any]:
        order_id = payment.external_ref or f"RVW-{uuid.uuid4().hex[:12].upper()}"
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
            "billing.firstname": (payment.payer_name or "Consumer").split()[0],
            "billing.lastname":  (payment.payer_name or "Consumer").split()[-1],
            "billing.address_1": "Dar es Salaam",
            "billing.city":      "Dar es Salaam",
            "billing.country":   "TZ",
            "billing.phone":     phone,
        }
        body_str = json.dumps(body_dict)
        headers  = self._headers(body_str)

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{settings.SELCOM_BASE_URL}/checkout/create-order",
                headers=headers, content=body_str,
            )
        data = resp.json()
        if data.get("resultcode") != "000":
            raise PaymentProviderError("selcom", data.get("result", resp.text[:200]))

        payment_url = data.get("data", [{}])[0].get("payment_gateway_url", "")
        log.info("selcom.initiated", order_id=order_id, phone=phone[:6]+"****")
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
        headers   = self._headers(body_str)
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{settings.SELCOM_BASE_URL}/checkout/order-status",
                headers=headers, content=body_str,
            )
        data = resp.json()
        raw_status = str(
            (data.get("data") or [{}])[0].get("payment_status", "")
        ).lower()
        status = _normalise_status(raw_status, {
            "complete": "success", "paid": "success",
            "canceled": "failed", "failed": "failed",
        })
        return {"status": status, "provider_response": data}

    async def refund(self, transaction: PaymentTransaction) -> Dict[str, Any]:
        raise PaymentProviderError("selcom", "Automated refunds not supported. Use Selcom portal.")


# ─────────────────────────────────────────────────────────────────────────────
# M-Pesa (Vodacom Tanzania)
# ─────────────────────────────────────────────────────────────────────────────

class MpesaProvider(BasePaymentProvider):
    """
    Vodacom M-Pesa Tanzania Open API.
    Supports: M-Pesa mobile money (push STK).

    Docs: https://openapiportal.m-pesa.com/

    Flow:
      1. Encrypt API key with RSA public key → session key
      2. POST /ipg/v2/vodacomTZN/c2bPayment/singleStage → initiate push
      3. Customer receives USSD prompt on phone
      4. Callback POST /webhooks/mpesa → confirmation
      5. POST /ipg/v2/vodacomTZN/queryTransactionStatus → verify

    Note: M-Pesa requires a valid session key every request.
    Session keys expire after ~24h.
    """
    name = PaymentProvider.MPESA
    _session_key: Optional[str] = None
    _session_key_ts: float = 0.0

    async def _get_session_key(self) -> str:
        """Encrypt MPESA_API_KEY with RSA public key to get session key."""
        # Refresh if older than 23 hours
        if self._session_key and (time.time() - self._session_key_ts) < 82800:
            return self._session_key

        try:
            from cryptography.hazmat.primitives import serialization, hashes
            from cryptography.hazmat.primitives.asymmetric import padding
            pub_key_bytes = base64.b64decode(settings.MPESA_PUBLIC_KEY)
            pub_key = serialization.load_der_public_key(pub_key_bytes)
            encrypted = pub_key.encrypt(
                settings.MPESA_API_KEY.encode(),
                padding.PKCS1v15(),
            )
            MpesaProvider._session_key = base64.b64encode(encrypted).decode()
            MpesaProvider._session_key_ts = time.time()
            return MpesaProvider._session_key
        except ImportError:
            raise PaymentProviderError(
                "mpesa",
                "cryptography package required for M-Pesa. "
                "pip install cryptography --break-system-packages"
            )

    async def initiate(self, payment: Payment, phone: str) -> Dict[str, Any]:
        session_key = await self._get_session_key()
        # M-Pesa wants phone without leading + (local format or MSISDN)
        msisdn = phone.lstrip("+")
        third_party_ref = payment.external_ref or f"RVW{uuid.uuid4().hex[:10].upper()}"

        async with httpx.AsyncClient(
            timeout=30,
            headers={
                "Authorization": f"Bearer {session_key}",
                "Origin": settings.PAYMENT_CALLBACK_BASE_URL,
            }
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
                "mpesa",
                data.get("output_ResponseDesc", resp.text[:200])
            )
        conv_id = data.get("output_ConversationID", third_party_ref)
        log.info("mpesa.initiated", conv_id=conv_id, phone=phone[:6]+"****")
        return {
            "provider_ref":      conv_id,
            "provider_order_id": third_party_ref,
            "status":            "pending",
            "provider_response": data,
        }

    async def verify(self, provider_ref: str) -> Dict[str, Any]:
        session_key = await self._get_session_key()
        third_party_ref = f"QRY{uuid.uuid4().hex[:8].upper()}"
        async with httpx.AsyncClient(
            timeout=15,
            headers={"Authorization": f"Bearer {session_key}",
                     "Origin": settings.PAYMENT_CALLBACK_BASE_URL}
        ) as client:
            resp = await client.get(
                f"{settings.MPESA_BASE_URL}/ipg/v2/vodacomTZN/queryTransactionStatus/",
                params={
                    "input_QueryReference":        provider_ref,
                    "input_ServiceProviderCode":   settings.MPESA_SERVICE_PROVIDER_CODE,
                    "input_ThirdPartyConversationID": third_party_ref,
                    "input_Country":               "TZN",
                },
            )
        data = resp.json()
        raw_status = data.get("output_ResponseCode", "")
        status = "success" if raw_status == "INS-0" else "failed"
        return {"status": status, "provider_response": data}

    async def refund(self, transaction: PaymentTransaction) -> Dict[str, Any]:
        raise PaymentProviderError("mpesa", "Refunds not yet supported via API. Use M-Pesa portal.")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_provider(provider: PaymentProvider) -> BasePaymentProvider:
    mapping = {
        PaymentProvider.AZAMPAY: AzamPayProvider,
        PaymentProvider.SELCOM:  SelcomProvider,
        PaymentProvider.MPESA:   MpesaProvider,
    }
    cls = mapping.get(provider)
    if not cls:
        raise ValueError(f"Unknown provider: {provider}")
    return cls()


def _azampay_network(phone: str) -> str:
    """Map Tanzanian phone number prefix to AzamPay network string."""
    digits = phone.lstrip("+")
    if digits.startswith("255") and len(digits) >= 6:
        prefix = digits[3:5]
    else:
        prefix = digits[:2]
    mapping = {
        "74": "Airtel", "75": "Airtel", "78": "Airtel",
        "71": "Tigo",   "65": "Tigo",   "67": "Tigo",
        "76": "Halotel", "77": "Halotel",
        "68": "TTCL",    "69": "TTCL",
        "61": "Vodacom", "62": "Vodacom",
        "73": "Vodacom",  # M-Pesa
    }
    return mapping.get(prefix, "Airtel")


def _normalise_status(raw: str, mapping: Dict[str, str]) -> str:
    return mapping.get(raw, "pending")

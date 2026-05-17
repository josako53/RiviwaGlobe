"""services/payment_gateway.py — Payment gateway integrations for subscriptions."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import uuid
from decimal import Decimal
from typing import Optional

import httpx
import structlog

from core.config import settings

log = structlog.get_logger(__name__)

USD_TO_TZS = Decimal("2600")   # approximate; update via FX service


def _to_tzs(usd: Decimal) -> int:
    return int(usd * USD_TO_TZS)


# ── AzamPay ──────────────────────────────────────────────────────────────────

async def _azampay_token() -> str:
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            f"{settings.AZAMPAY_BASE_URL}/AppRegistration/GenerateToken",
            json={
                "appName": settings.AZAMPAY_APP_NAME,
                "clientId": settings.AZAMPAY_CLIENT_ID,
                "clientSecret": settings.AZAMPAY_CLIENT_SECRET,
            },
        )
        r.raise_for_status()
        return r.json()["data"]["accessToken"]


async def charge_azampay(phone: str, amount_usd: Decimal, invoice_id: str, invoice_number: str) -> dict:
    token = await _azampay_token()
    amount_tzs = _to_tzs(amount_usd)
    external_id = str(uuid.uuid4())

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{settings.AZAMPAY_CHECKOUT_URL}/api/v1/Partner/PostCheckout",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "accountNumber": phone.lstrip("+"),
                "additionalProperties": {"invoiceId": invoice_id},
                "amount": str(amount_tzs),
                "currency": "TZS",
                "externalId": external_id,
                "merchantId": settings.AZAMPAY_CLIENT_ID,
                "provider": "Airtel",
                "callbackUrl": f"{settings.PAYMENT_CALLBACK_BASE_URL}/api/v1/subscriptions/webhooks/azampay",
            },
        )
    data = r.json()
    log.info("azampay.charge_initiated", invoice_id=invoice_id, status=data.get("success"))
    return {"provider": "azampay", "external_id": external_id, "raw": data, "success": data.get("success", False)}


# ── M-Pesa ────────────────────────────────────────────────────────────────────

def _mpesa_encrypt_key() -> str:
    from cryptography.hazmat.primitives import serialization, hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    pub_key_pem = (
        "-----BEGIN PUBLIC KEY-----\n"
        + settings.MPESA_PUBLIC_KEY + "\n"
        + "-----END PUBLIC KEY-----"
    )
    from cryptography.hazmat.backends import default_backend
    public_key = serialization.load_pem_public_key(pub_key_pem.encode(), backend=default_backend())
    encrypted = public_key.encrypt(settings.MPESA_API_KEY.encode(), padding.PKCS1v15())
    return base64.b64encode(encrypted).decode()


async def charge_mpesa(phone: str, amount_usd: Decimal, invoice_id: str) -> dict:
    amount_tzs = _to_tzs(amount_usd)
    try:
        session_key = _mpesa_encrypt_key()
    except Exception as exc:
        log.warning("mpesa.key_encrypt_failed", error=str(exc))
        return {"provider": "mpesa", "success": False, "error": str(exc)}

    async with httpx.AsyncClient(timeout=30, verify=False) as client:
        r = await client.get(
            f"{settings.MPESA_BASE_URL}/v1/sandbox/ipg/v2/vodacomTZN/getSession/",
            headers={"Authorization": f"Bearer {session_key}", "Origin": "developer.vodacom.co.tz"},
        )
        if r.status_code != 200:
            return {"provider": "mpesa", "success": False, "error": r.text}
        session_token = r.json().get("output_SessionID", "")

        ref = invoice_id[:12]
        r2 = await client.post(
            f"{settings.MPESA_BASE_URL}/v1/sandbox/ipg/v2/vodacomTZN/c2bPayment/singleStage/",
            headers={"Authorization": f"Bearer {session_token}", "Origin": "developer.vodacom.co.tz"},
            json={
                "input_Amount": str(amount_tzs),
                "input_Country": "TZA",
                "input_Currency": "TZS",
                "input_CustomerMSISDN": phone.lstrip("+"),
                "input_ServiceProviderCode": settings.MPESA_SERVICE_PROVIDER_CODE,
                "input_ThirdPartyConversationID": ref,
                "input_TransactionReference": ref,
                "input_PurchasedItemsDesc": f"Riviwa subscription {invoice_id}",
            },
        )
    data = r2.json()
    success = data.get("output_ResponseCode") == "INS-0"
    log.info("mpesa.charge", invoice_id=invoice_id, success=success)
    return {"provider": "mpesa", "success": success, "raw": data}


# ── Selcom ────────────────────────────────────────────────────────────────────

def _selcom_headers(body: str) -> dict:
    digest = base64.b64encode(hashlib.sha256(body.encode()).digest()).decode()
    sig = base64.b64encode(
        hmac.new(settings.SELCOM_API_SECRET.encode(), body.encode(), hashlib.sha256).digest()
    ).decode()
    return {
        "Content-Type": "application/json;charset=utf-8",
        "Authorization": f"SELCOM {settings.SELCOM_API_KEY}",
        "Digest-Method": "HS256",
        "Digest": digest,
        "Signature": sig,
        "signed-fields": "content-type,accept,digest-method,digest",
        "Accept": "application/json",
        "timestamp": __import__("datetime").datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S%z"),
    }


async def charge_selcom(phone: str, amount_usd: Decimal, invoice_id: str) -> dict:
    amount_tzs = _to_tzs(amount_usd)
    body = json.dumps({
        "vendor": settings.SELCOM_VENDOR,
        "order_id": invoice_id[:20],
        "buyer_email": "noreply@riviwa.com",
        "buyer_name": "Riviwa Subscriber",
        "buyer_phone": phone.lstrip("+"),
        "amount": str(amount_tzs),
        "currency": "TZS",
        "redirect_url": f"{settings.PAYMENT_CALLBACK_BASE_URL}/api/v1/subscriptions/checkout/success",
        "cancel_url": f"{settings.PAYMENT_CALLBACK_BASE_URL}/api/v1/subscriptions/checkout/cancel",
        "webhook": f"{settings.PAYMENT_CALLBACK_BASE_URL}/api/v1/subscriptions/webhooks/selcom",
        "no_of_items": 1,
    })
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{settings.SELCOM_BASE_URL}/checkout/create-order",
            headers=_selcom_headers(body),
            content=body,
        )
    data = r.json()
    success = data.get("resultcode") == "000"
    log.info("selcom.charge", invoice_id=invoice_id, success=success)
    return {"provider": "selcom", "success": success, "raw": data,
            "payment_url": data.get("data", {}).get("payment_url")}


# ── Stripe ────────────────────────────────────────────────────────────────────

async def charge_stripe(stripe_payment_method_id: str, amount_usd: Decimal, invoice_id: str) -> dict:
    amount_cents = int(amount_usd * 100)
    async with httpx.AsyncClient(timeout=30) as client:
        # Create PaymentIntent
        r = await client.post(
            "https://api.stripe.com/v1/payment_intents",
            auth=(settings.STRIPE_SECRET_KEY, ""),
            data={
                "amount": str(amount_cents),
                "currency": "usd",
                "payment_method": stripe_payment_method_id,
                "confirm": "true",
                "metadata[invoice_id]": invoice_id,
                "description": f"Riviwa subscription — invoice {invoice_id}",
            },
        )
    data = r.json()
    success = data.get("status") in ("succeeded", "requires_capture")
    log.info("stripe.charge", invoice_id=invoice_id, success=success, status=data.get("status"))
    return {
        "provider": "stripe",
        "success": success,
        "payment_intent_id": data.get("id"),
        "status": data.get("status"),
        "raw": data,
    }


# ── Dispatcher ────────────────────────────────────────────────────────────────

async def process_payment(
    method_type: str,
    phone: Optional[str],
    stripe_pm_id: Optional[str],
    amount_usd: Decimal,
    invoice_id: str,
    invoice_number: str,
) -> dict:
    if method_type == "azampay":
        return await charge_azampay(phone, amount_usd, invoice_id, invoice_number)
    if method_type == "mpesa":
        return await charge_mpesa(phone, amount_usd, invoice_id)
    if method_type == "selcom":
        return await charge_selcom(phone, amount_usd, invoice_id)
    if method_type == "stripe_card":
        return await charge_stripe(stripe_pm_id, amount_usd, invoice_id)
    if method_type == "bank_transfer":
        return {"provider": "bank_transfer", "success": True, "manual": True,
                "instructions": f"Transfer to Riviwa account. Reference: {invoice_number}"}
    raise ValueError(f"Unknown payment method type: {method_type}")

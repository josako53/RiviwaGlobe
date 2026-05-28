"""providers/airtel.py — Airtel Money Tanzania (Collection + Refund + Enquiry + Disbursement).

Docs: https://openapi.airtel.co.tz (production)
      https://openapiuat.airtel.co.tz (staging)

OAuth2 client-credentials flow. Phone without country code (e.g. 75123456, not +25575123456).

Status codes:
  TS  — Transaction Success
  TF  — Transaction Failed
  TA  — Transaction Ambiguous (still processing)
  TIP — Transaction in Progress
  TE  — Transaction Expired

Collection API response codes (full):
  DP00800001000 — Ambiguous       — still processing; do enquiry to get final status
  DP00800001001 — Success         — transaction successful
  DP00800001002 — Incorrect PIN   — user entered wrong PIN
  DP00800001003 — Exceeds limit   — user exceeded wallet transaction limit
  DP00800001004 — Invalid Amount  — amount below minimum allowed
  DP00800001005 — Invalid Txn ID  — user did not enter PIN (session expired)
  DP00800001006 — In process      — transaction pending; check again shortly
  DP00800001007 — No balance      — user wallet has insufficient funds
  DP00800001008 — Refused         — transaction refused by Airtel
  DP00800001010 — Payee barred    — payee not registered / barred on Airtel Money
  DP00800001024 — Timed out       — transaction timed out
  DP00800001025 — Not found       — transaction not found (wrong ID or too early)
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

# Maps Airtel Collection API response_code → (outcome, user-facing message)
# outcome: "pending" | "failed" | "ambiguous"
_COLLECTION_ERROR_MAP: Dict[str, tuple[str, str]] = {
    "DP00800001000": ("ambiguous", "Transaction is still processing. Please wait and check your status shortly."),
    "DP00800001002": ("failed",    "Incorrect PIN entered. Please try again with the correct Airtel Money PIN."),
    "DP00800001003": ("failed",    "Transaction limit exceeded. Your Airtel Money wallet has reached its allowed limit."),
    "DP00800001004": ("failed",    "Invalid amount. The amount is below the minimum allowed by Airtel Money."),
    "DP00800001005": ("failed",    "PIN not entered. The USSD session expired before you entered your PIN. Please try again."),
    "DP00800001007": ("failed",    "Insufficient balance. Your Airtel Money wallet does not have enough funds."),
    "DP00800001008": ("failed",    "Transaction refused by Airtel Money. Please contact Airtel support."),
    "DP00800001010": ("failed",    "Payment not permitted. Your Airtel Money account may be barred or not registered."),
    "DP00800001024": ("failed",    "Transaction timed out. Please try again."),
    "DP00800001025": ("failed",    "Transaction not found. Please verify the reference and try again."),
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
        """Normalise to 9-digit local format — Airtel wants e.g. 788230980, not 0788230980 or +255788230980."""
        phone = phone.strip().lstrip("+")
        if phone.startswith("255"):
            phone = phone[3:]
        if phone.startswith("0") and len(phone) == 10:
            phone = phone[1:]
        return phone

    async def initiate(self, payment: Payment, phone: str) -> Dict[str, Any]:
        token   = await self._get_token()
        msisdn  = self._strip_country_code(phone)
        txn_id  = payment.external_ref or f"RVW-{payment.id.hex[:12].upper()}"
        amount  = payment.amount

        amount_val = int(amount) if float(amount) == int(amount) else float(amount)
        body = {
            "reference": payment.description or "Riviwa payment",
            "subscriber": {
                "country":  "TZ",
                "currency": "TZS",
                "msisdn":   msisdn,
            },
            "transaction": {
                "amount":   amount_val,
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

        # DP00800001001 = success, DP00800001006 = in process (both OK for initiation)
        # DP00800001000 = ambiguous (still processing — treat as pending, caller should enquire)
        allowed = {"DP00800001001", "DP00800001006", "DP00800001000"}
        if not success and resp_code not in allowed:
            log.error("airtel.initiate_rejected",
                      resp_code=resp_code,
                      message=status_block.get("message"),
                      result_code=status_block.get("result_code"),
                      raw_response=data)
            mapped_error = _COLLECTION_ERROR_MAP.get(resp_code)
            if mapped_error:
                _, user_msg = mapped_error
                raise PaymentProviderError("airtel", f"{user_msg} [{resp_code}]")
            raise PaymentProviderError(
                "airtel",
                f"{status_block.get('message', 'Unknown error')} [{resp_code}]"
            )

        txn_data    = data.get("data", {}).get("transaction", {})
        airtel_txn  = txn_data.get("id", txn_id)
        # Ambiguous on initiation — mark as pending so enquiry can resolve it
        init_status = "ambiguous" if resp_code == "DP00800001000" else "pending"

        log.info("airtel.initiated", txn_id=txn_id, msisdn=msisdn[:4] + "****",
                 resp_code=resp_code)
        return {
            "provider_ref":      txn_id,        # our ID — used for enquiry
            "provider_order_id": airtel_txn,     # Airtel's ID
            "status":            init_status,
            "resp_code":         resp_code,
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
        status_block = data.get("status", {})
        resp_code    = status_block.get("response_code", "")
        txn_data   = data.get("data", {}).get("transaction", {})
        raw_status = txn_data.get("status", "")
        status     = _AIRTEL_STATUS_MAP.get(raw_status, "pending")
        receipt    = txn_data.get("airtel_money_id")

        # Enrich failure reason from error map when status is failed
        failure_reason = None
        if status == "failed":
            mapped_error = _COLLECTION_ERROR_MAP.get(resp_code)
            failure_reason = mapped_error[1] if mapped_error else status_block.get("message")

        log.info("airtel.verify", provider_ref=provider_ref, raw_status=raw_status,
                 resp_code=resp_code, status=status)
        return {
            "status":            status,
            "receipt":           receipt,
            "resp_code":         resp_code,
            "failure_reason":    failure_reason,
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

    # ── Disbursements (V2) ────────────────────────────────────────────────────

    def _encrypt_pin(self, pin: str) -> str:
        """
        RSA-encrypt the 4-digit disbursement PIN using Airtel's public key.

        Airtel requires: RSA/ECB/PKCS1Padding (PKCS#1 v1.5), 1024-bit key.
        Key format: base64-encoded PEM or DER (SubjectPublicKeyInfo).
        Returns base64-encoded ciphertext.
        """
        if not settings.AIRTEL_PUBLIC_KEY:
            raise PaymentProviderError(
                "airtel",
                "AIRTEL_PUBLIC_KEY not configured. Set it in .env to enable disbursements."
            )
        try:
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.asymmetric import padding as asym_padding

            raw = settings.AIRTEL_PUBLIC_KEY.strip()

            # Support both PEM ("-----BEGIN PUBLIC KEY-----") and raw base64 DER
            if raw.startswith("-----"):
                pub_key = serialization.load_pem_public_key(raw.encode())
            else:
                pub_key = serialization.load_der_public_key(base64.b64decode(raw))

            # Airtel: RSA/ECB/PKCS1Padding = PKCS#1 v1.5 (NOT OAEP)
            encrypted = pub_key.encrypt(pin.encode(), asym_padding.PKCS1v15())
            return base64.b64encode(encrypted).decode()
        except Exception as exc:
            raise PaymentProviderError("airtel", f"PIN encryption failed: {exc}")

    async def disburse(
        self,
        transaction_id:   str,
        payee_msisdn:     str,
        payee_name:       Optional[str],
        amount:           int,
        reference:        str,
        transaction_type: str = "B2B",
    ) -> Dict[str, Any]:
        """
        POST /standard/v2/disbursements/ — send funds to an Airtel wallet.

        transaction_id: unique ID we generate (used for status enquiry).
        payee_msisdn:   phone WITHOUT country code, e.g. '756789012'.
        transaction_type: 'B2B' for internal staff, 'B2C' for consumer payouts.

        Response statuses: TS=success TF=failed TA=ambiguous TIP=in-progress
        """
        if not settings.AIRTEL_DISBURSEMENT_PIN:
            raise PaymentProviderError(
                "airtel",
                "AIRTEL_DISBURSEMENT_PIN not configured. Set the 4-digit merchant PIN in .env."
            )

        token      = await self._get_token()
        msisdn     = self._strip_country_code(payee_msisdn)
        enc_pin    = self._encrypt_pin(settings.AIRTEL_DISBURSEMENT_PIN)

        amount_val = int(amount) if float(amount) == int(amount) else float(amount)
        body = {
            "payee": {
                "currency": "TZS",
                "msisdn":   msisdn,
                "name":     payee_name or "",
            },
            "reference": reference,
            "pin":        enc_pin,
            "transaction": {
                "amount": amount_val,
                "id":     transaction_id,
                "type":   transaction_type,
            },
        }

        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{self._base_url()}/standard/v2/disbursements/",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type":  "application/json",
                    "Accept":        "*/*",
                    "X-Country":     "TZ",
                    "X-Currency":    "TZS",
                },
                json=body,
            )

        data         = r.json()
        status_block = data.get("status", {})
        resp_code    = status_block.get("response_code", "")
        success      = status_block.get("success", False)

        # DP00900001001 = Success, DP00900001006 = Processing (both OK for initiation)
        if not success and resp_code not in ("DP00900001001", "DP00900001006",
                                             "DP00900001000"):  # ambiguous = still processing
            log.error("airtel.disburse_rejected",
                      resp_code=resp_code,
                      message=status_block.get("message"),
                      raw_response=data)
            raise PaymentProviderError(
                "airtel",
                f"{status_block.get('message', 'Disbursement failed')} [{resp_code}]",
            )

        txn_data         = data.get("data", {}).get("transaction", {})
        airtel_money_id  = txn_data.get("airtel_money_id")
        airtel_ref_id    = txn_data.get("reference_id")
        raw_status       = txn_data.get("status", "")
        # DP00900001001 + success=True means the transfer completed immediately (no TS in txn_data)
        if success and resp_code == "DP00900001001":
            mapped_status = "success"
        else:
            mapped_status = _AIRTEL_STATUS_MAP.get(raw_status, "processing")

        log.info(
            "airtel.disburse",
            transaction_id=transaction_id,
            msisdn=msisdn[:3] + "****",
            amount=amount,
            resp_code=resp_code,
            raw_status=raw_status,
        )
        return {
            "status":            mapped_status,
            "our_transaction_id": transaction_id,
            "airtel_money_id":   airtel_money_id,
            "airtel_reference_id": airtel_ref_id,
            "resp_code":         resp_code,
            "provider_response": data,
        }

    async def enquiry_disbursement(self, transaction_id: str, transaction_type: str = "B2B") -> Dict[str, Any]:
        """
        GET /standard/v2/disbursements/{id} — poll transaction status.
        Call at least 1 minute after disburse() to allow Airtel time to process.
        """
        token = await self._get_token()

        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"{self._base_url()}/standard/v2/disbursements/{transaction_id}",
                params={"transactionType": transaction_type},
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
        status     = _AIRTEL_STATUS_MAP.get(raw_status, "processing")
        message    = txn_data.get("message", "")

        log.info("airtel.enquiry_disbursement",
                 transaction_id=transaction_id, raw_status=raw_status)
        return {
            "status":            status,
            "raw_status":        raw_status,
            "message":           message,
            "provider_response": data,
        }

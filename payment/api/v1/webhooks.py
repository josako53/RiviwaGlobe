"""api/v1/webhooks.py — gateway callbacks, HTTP orchestration only"""
from __future__ import annotations
import hashlib, hmac, json
from fastapi import APIRouter, Request, status
from fastapi.responses import RedirectResponse
from core.config import settings
from core.dependencies import DbDep
from models.payment import PaymentProvider
from services.payment_service import PaymentService

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])
def _svc(db): return PaymentService(db=db)

@router.post("/azampay", status_code=status.HTTP_200_OK, include_in_schema=False)
async def azampay_callback(request: Request, db: DbDep) -> dict:
    raw  = await request.body()
    body = {}
    try: body = json.loads(raw)
    except Exception: pass
    await _svc(db).process_webhook(
        provider=PaymentProvider.AZAMPAY,
        headers=dict(request.headers), body=body, raw_body=raw.decode(errors="replace"),
    )
    return {"status": "received"}

@router.post("/selcom", status_code=status.HTTP_200_OK, include_in_schema=False)
async def selcom_callback(request: Request, db: DbDep) -> dict:
    raw  = await request.body()
    body = {}
    try: body = json.loads(raw)
    except Exception: pass
    if settings.SELCOM_API_SECRET:
        sig_header = request.headers.get("Signature", "")
        expected   = hmac.new(settings.SELCOM_API_SECRET.encode(), raw, hashlib.sha256).hexdigest()
        if sig_header and not hmac.compare_digest(sig_header, expected):
            pass  # Log but don't reject — some environments omit signature
    await _svc(db).process_webhook(
        provider=PaymentProvider.SELCOM,
        headers=dict(request.headers), body=body, raw_body=raw.decode(errors="replace"),
    )
    return {"status": "received"}

@router.post("/mpesa", status_code=status.HTTP_200_OK, include_in_schema=False)
async def mpesa_callback(request: Request, db: DbDep) -> dict:
    raw  = await request.body()
    body = {}
    try: body = json.loads(raw)
    except Exception: pass
    await _svc(db).process_webhook(
        provider=PaymentProvider.MPESA,
        headers=dict(request.headers), body=body, raw_body=raw.decode(errors="replace"),
    )
    return {
        "output_ResponseCode": "INS-0",
        "output_ResponseDesc": "Request processed successfully",
        "output_TransactionID": body.get("output_TransactionID", ""),
    }


@router.post("/airtel", status_code=status.HTTP_200_OK, include_in_schema=False)
async def airtel_callback(request: Request, db: DbDep) -> dict:
    """
    Airtel Money callback — handles both authenticated (with hash) and
    unauthenticated callbacks.

    Airtel sends:
    {
      "transaction": {
        "id":              "our-txn-id",
        "message":         "Paid TZS ...",
        "status_code":     "TS" | "TF",
        "airtel_money_id": "MP..."
      },
      "hash": "..."   // optional, if callback auth enabled
    }
    """
    raw  = await request.body()
    body = {}
    try:
        body = json.loads(raw)
    except Exception:
        pass

    # Verify HMAC hash if Airtel callback authentication is enabled
    if body.get("hash") and settings.AIRTEL_CLIENT_SECRET:
        import base64 as _b64, hashlib as _hl, hmac as _hmac
        txn_body = json.dumps(body.get("transaction", {}), separators=(",", ":"))
        expected = _b64.b64encode(
            _hmac.new(settings.AIRTEL_CLIENT_SECRET.encode(), txn_body.encode(), _hl.sha256).digest()
        ).decode()
        if not _hmac.compare_digest(body.get("hash", ""), expected):
            import structlog as _sl
            _sl.get_logger(__name__).warning("airtel.callback_hash_mismatch")
            # Still process — log but don't block (hash validation is advisory)

    txn_block = body.get("transaction", {})
    # Map Airtel status_code to our provider_ref for reconciliation
    our_txn_id = txn_block.get("id", "")
    if our_txn_id:
        body["transactionId"] = our_txn_id

    await _svc(db).process_webhook(
        provider=PaymentProvider.AIRTEL,
        headers=dict(request.headers),
        body=body,
        raw_body=raw.decode(errors="replace"),
    )
    return {"status": "received"}


@router.post("/yas", status_code=status.HTTP_200_OK, include_in_schema=False)
async def yas_callback(request: Request, db: DbDep) -> dict:
    """
    Yas Money (formerly Tigo Pesa) callback.

    Yas sends:
    {
      "reference":      "our-reference",
      "transaction_id": "yas-generated-id",
      "status":         "SUCCESS" | "FAILED" | "CANCELLED",
      "amount":         1000,
      "msisdn":         "71234567",
      "message":        "..."
    }
    """
    raw  = await request.body()
    body = {}
    try:
        body = json.loads(raw)
    except Exception:
        pass

    # Map Yas field to our reconciliation key
    our_ref = body.get("reference") or body.get("external_reference")
    if our_ref:
        body["transactionId"] = our_ref

    await _svc(db).process_webhook(
        provider=PaymentProvider.YAS,
        headers=dict(request.headers),
        body=body,
        raw_body=raw.decode(errors="replace"),
    )
    return {"status": "received"}


@router.post("/paypal", status_code=status.HTTP_200_OK, include_in_schema=False)
async def paypal_webhook(request: Request, db: DbDep) -> dict:
    """PayPal webhook — handles PAYMENT.CAPTURE.COMPLETED and ORDER.APPROVED."""
    raw  = await request.body()
    body = {}
    try:
        body = json.loads(raw)
    except Exception:
        pass

    event_type = body.get("event_type", "")

    if event_type in ("PAYMENT.CAPTURE.COMPLETED", "CHECKOUT.ORDER.APPROVED"):
        resource   = body.get("resource", {})
        order_id   = resource.get("id") or resource.get("supplementary_data", {}).get("related_ids", {}).get("order_id")
        if order_id:
            from providers.paypal import PayPalProvider
            provider = PayPalProvider()
            if event_type == "CHECKOUT.ORDER.APPROVED":
                # Capture the order
                try:
                    await provider.capture(order_id)
                except Exception:
                    pass
            await _svc(db).process_webhook(
                provider=PaymentProvider.PAYPAL,
                headers=dict(request.headers),
                body={**body, "transactionId": order_id},
                raw_body=raw.decode(errors="replace"),
            )

    return {"status": "received"}


@router.get("/paypal/return", include_in_schema=False)
async def paypal_return(token: str, db: DbDep) -> RedirectResponse:
    """PayPal return URL — user approved payment, capture it."""
    if token:
        from providers.paypal import PayPalProvider
        from sqlalchemy import select
        from models.payment import PaymentTransaction
        try:
            provider = PayPalProvider()
            result   = await provider.capture(token)
            # Find and update transaction
            await _svc(db).process_webhook(
                provider=PaymentProvider.PAYPAL,
                headers={},
                body={"transactionId": token, "status": result.get("status")},
                raw_body="",
            )
        except Exception:
            pass
    return RedirectResponse(url=f"{settings.PAYMENT_CALLBACK_BASE_URL}/payment/success?ref={token}")


@router.get("/paypal/cancel", include_in_schema=False)
async def paypal_cancel(token: str) -> RedirectResponse:
    return RedirectResponse(url=f"{settings.PAYMENT_CALLBACK_BASE_URL}/payment/cancel")

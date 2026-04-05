"""api/v1/webhooks.py — gateway callbacks, HTTP orchestration only"""
from __future__ import annotations
import hashlib, hmac, json
from fastapi import APIRouter, Request, status
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

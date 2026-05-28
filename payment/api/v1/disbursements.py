"""
api/v1/disbursements.py — Airtel Money V2 Disbursements
════════════════════════════════════════════════════════════════════════════════
Outbound payments from the platform to Airtel Money wallets.

Access:  Platform admin / super_admin ONLY.  Not accessible to org users.

Airtel V2 Disbursement API docs:
  POST /standard/v2/disbursements/      — send funds
  GET  /standard/v2/disbursements/{id}  — enquiry (poll after ≥1 min)

Transaction type:
  B2B — business-to-business (default; internal staff, agents, approved payees)
  B2C — business-to-consumer (direct consumer payouts; requires explicit override)

Lifecycle:
  PENDING → PROCESSING → SUCCESS
                       ↘ FAILED
                       ↘ AMBIGUOUS  (TA — re-enquire after 1 minute)

Endpoints
──────────
  POST   /payments/disbursements              Create & send disbursement
  GET    /payments/disbursements              List disbursements (with filters)
  GET    /payments/disbursements/{id}         Get single disbursement
  POST   /payments/disbursements/{id}/enquiry Poll Airtel for latest status
  DELETE /payments/disbursements/{id}         Cancel PENDING disbursement
════════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import structlog
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import DbDep, PlatformAdminDep
from core.exceptions import PaymentProviderError
from models.payment import Disbursement, DisbursementStatus
from providers.airtel import AirtelMoneyProvider

log    = structlog.get_logger(__name__)
router = APIRouter(prefix="/payments/disbursements", tags=["Disbursements"])

_DISBURSE_STATUS_MAP = {
    "success":    DisbursementStatus.SUCCESS,
    "failed":     DisbursementStatus.FAILED,
    "pending":    DisbursementStatus.PROCESSING,
    "processing": DisbursementStatus.PROCESSING,
}


def _out(d: Disbursement) -> dict:
    return {
        "id":                  str(d.id),
        "payee_msisdn":        d.payee_msisdn,
        "payee_name":          d.payee_name,
        "amount":              d.amount,
        "currency":            d.currency,
        "reference":           d.reference,
        "description":         d.description,
        "transaction_type":    d.transaction_type,
        "org_id":              str(d.org_id) if d.org_id else None,
        "notes":               d.notes,
        "status":              d.status,
        "our_transaction_id":  d.our_transaction_id,
        "airtel_money_id":     d.airtel_money_id,
        "airtel_reference_id": d.airtel_reference_id,
        "failure_reason":      d.failure_reason,
        "initiated_by":        str(d.initiated_by),
        "created_at":          d.created_at.isoformat(),
        "updated_at":          d.updated_at.isoformat(),
        "completed_at":        d.completed_at.isoformat() if d.completed_at else None,
    }


async def _get_or_404(disbursement_id: uuid.UUID, db: AsyncSession) -> Disbursement:
    d = await db.get(Disbursement, disbursement_id)
    if not d:
        raise HTTPException(status_code=404, detail={"error": "DISBURSEMENT_NOT_FOUND"})
    return d


# ── POST /payments/disbursements ──────────────────────────────────────────────

@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create and send an Airtel Money disbursement",
    description=(
        "Initiates an outbound payment from the platform's Airtel merchant account "
        "to the specified Airtel Money wallet.\n\n"
        "**Restricted to platform admin / super_admin only.**\n\n"
        "The call is synchronous — it sends the disbursement request to Airtel and "
        "returns the initial status immediately. For `B2B` transactions Airtel often "
        "returns `TIP` (in progress) immediately; use `POST /{id}/enquiry` after at "
        "least **1 minute** to get the final `TS` (success) or `TF` (failed) status.\n\n"
        "**PIN encryption** is handled server-side using the `AIRTEL_PUBLIC_KEY` and "
        "`AIRTEL_DISBURSEMENT_PIN` configured in the platform `.env`."
    ),
)
async def create_disbursement(
    body:  Dict[str, Any],
    db:    DbDep,
    token: PlatformAdminDep,
) -> dict:
    """
    Required body fields:
    - payee_msisdn     : Airtel phone WITHOUT country code, e.g. "756789012"
    - amount           : integer amount in TZS
    - reference        : reference string shown on recipient's Airtel receipt

    Optional:
    - payee_name       : name of recipient
    - description      : internal description (not sent to Airtel)
    - transaction_type : "B2B" (default) | "B2C"
    - org_id           : org context for reporting
    - notes            : internal admin notes
    """
    payee_msisdn = str(body.get("payee_msisdn") or "").strip()
    if not payee_msisdn:
        raise HTTPException(status_code=422, detail={"error": "payee_msisdn is required"})

    try:
        amount = int(body["amount"])
    except (KeyError, ValueError, TypeError):
        raise HTTPException(status_code=422, detail={"error": "amount must be a positive integer (TZS)"})
    if amount <= 0:
        raise HTTPException(status_code=422, detail={"error": "amount must be greater than 0"})

    reference = str(body.get("reference") or "").strip()
    if not reference:
        raise HTTPException(status_code=422, detail={"error": "reference is required"})

    transaction_type = (body.get("transaction_type") or "B2B").upper()
    if transaction_type not in ("B2B", "B2C"):
        raise HTTPException(status_code=422, detail={"error": "transaction_type must be B2B or B2C"})

    our_txn_id = f"RVW-DSB-{uuid.uuid4().hex[:16].upper()}"

    disbursement = Disbursement(
        payee_msisdn     = payee_msisdn,
        payee_name       = body.get("payee_name"),
        amount           = float(amount),
        currency         = "TZS",
        reference        = reference,
        description      = body.get("description"),
        transaction_type = transaction_type,
        org_id           = uuid.UUID(str(body["org_id"])) if body.get("org_id") else None,
        notes            = body.get("notes"),
        status           = DisbursementStatus.PENDING.value,
        our_transaction_id = our_txn_id,
        initiated_by     = token.sub,
    )
    db.add(disbursement)
    await db.flush()

    # Send to Airtel
    provider = AirtelMoneyProvider()
    try:
        result = await provider.disburse(
            transaction_id   = our_txn_id,
            payee_msisdn     = payee_msisdn,
            payee_name       = body.get("payee_name"),
            amount           = amount,
            reference        = reference,
            transaction_type = transaction_type,
        )
        mapped = _DISBURSE_STATUS_MAP.get(result["status"], DisbursementStatus.PROCESSING)
        disbursement.status              = mapped.value
        disbursement.airtel_money_id     = result.get("airtel_money_id")
        disbursement.airtel_reference_id = result.get("airtel_reference_id")
        disbursement.raw_response        = result.get("provider_response")
        if mapped in (DisbursementStatus.SUCCESS, DisbursementStatus.FAILED):
            disbursement.completed_at = datetime.now(timezone.utc)

    except PaymentProviderError as exc:
        disbursement.status         = DisbursementStatus.FAILED.value
        disbursement.failure_reason = str(exc)
        disbursement.completed_at   = datetime.now(timezone.utc)
        log.error("disbursement.airtel_error", our_txn_id=our_txn_id, error=str(exc))

    db.add(disbursement)
    await db.commit()
    await db.refresh(disbursement)

    log.info("disbursement.created",
             id=str(disbursement.id), status=disbursement.status,
             amount=amount, msisdn=payee_msisdn[:3] + "****")
    return _out(disbursement)


# ── GET /payments/disbursements ───────────────────────────────────────────────

@router.get(
    "",
    status_code=200,
    summary="List disbursements",
    description=(
        "Returns a paginated list of all disbursements. "
        "Filter by `status`, `org_id`, or `transaction_type`.\n\n"
        "**Restricted to platform admin / super_admin only.**"
    ),
)
async def list_disbursements(
    db:               DbDep,
    token:            PlatformAdminDep,
    org_id:           Optional[uuid.UUID] = Query(default=None),
    status_filter:    Optional[str]       = Query(default=None, alias="status",
                                                   description="pending | processing | success | failed | ambiguous | cancelled"),
    transaction_type: Optional[str]       = Query(default=None, description="B2B | B2C"),
    page:             int                 = Query(default=1, ge=1),
    size:             int                 = Query(default=20, ge=1, le=100),
) -> dict:
    from sqlalchemy import func
    q = select(Disbursement)
    if org_id:
        q = q.where(Disbursement.org_id == org_id)
    if status_filter:
        q = q.where(Disbursement.status == status_filter.lower())  # plain string compare (VARCHAR col)
    if transaction_type:
        q = q.where(Disbursement.transaction_type == transaction_type.upper())

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    rows  = (await db.execute(
        q.order_by(Disbursement.created_at.desc()).offset((page - 1) * size).limit(size)
    )).scalars().all()

    return {"total": total, "page": page, "size": size, "items": [_out(d) for d in rows]}


# ── GET /payments/disbursements/{id} ─────────────────────────────────────────

@router.get(
    "/{disbursement_id}",
    status_code=200,
    summary="Get a single disbursement",
)
async def get_disbursement(
    disbursement_id: uuid.UUID,
    db:              DbDep,
    token:           PlatformAdminDep,
) -> dict:
    return _out(await _get_or_404(disbursement_id, db))


# ── POST /payments/disbursements/{id}/enquiry ─────────────────────────────────

@router.post(
    "/{disbursement_id}/enquiry",
    status_code=200,
    summary="Poll Airtel for latest disbursement status",
    description=(
        "Queries Airtel's `GET /standard/v2/disbursements/{id}` endpoint to get "
        "the current status of a disbursement.\n\n"
        "**Recommended:** Wait at least **1 minute** after the initial disbursement "
        "before calling this — Airtel needs time to process.\n\n"
        "Useful for resolving `AMBIGUOUS` (`TA`) and `PROCESSING` (`TIP`) states.\n\n"
        "Updates the disbursement record in the DB with the latest status."
    ),
)
async def enquiry_disbursement(
    disbursement_id: uuid.UUID,
    db:              DbDep,
    token:           PlatformAdminDep,
) -> dict:
    d = await _get_or_404(disbursement_id, db)

    if d.status in (DisbursementStatus.SUCCESS.value, DisbursementStatus.CANCELLED.value):
        return {**_out(d), "note": f"Already in terminal state: {d.status}"}

    provider = AirtelMoneyProvider()
    try:
        result     = await provider.enquiry_disbursement(d.our_transaction_id, d.transaction_type)
        mapped     = _DISBURSE_STATUS_MAP.get(result["status"], DisbursementStatus.PROCESSING)
        # AMBIGUOUS maps to its own status for clarity
        if result.get("raw_status") == "TA":
            mapped = DisbursementStatus.AMBIGUOUS

        d.status       = mapped.value
        d.raw_response = result.get("provider_response")
        if mapped in (DisbursementStatus.SUCCESS, DisbursementStatus.FAILED,
                      DisbursementStatus.AMBIGUOUS):
            d.failure_reason = result.get("message") if mapped == DisbursementStatus.FAILED else None
            if mapped == DisbursementStatus.SUCCESS:
                d.completed_at = datetime.now(timezone.utc)
    except PaymentProviderError as exc:
        log.warning("disbursement.enquiry_error", id=str(d.id), error=str(exc))
        raise HTTPException(status_code=502, detail={"error": "AIRTEL_ENQUIRY_FAILED", "detail": str(exc)})

    db.add(d)
    await db.commit()
    await db.refresh(d)
    return _out(d)


# ── DELETE /payments/disbursements/{id} ───────────────────────────────────────

@router.delete(
    "/{disbursement_id}",
    status_code=200,
    summary="Cancel a PENDING disbursement",
    description=(
        "Cancels a disbursement that has not yet been sent to Airtel (`status=pending`).\n\n"
        "Once a disbursement is in `PROCESSING` or later it **cannot** be cancelled here — "
        "contact Airtel support for reversal."
    ),
)
async def cancel_disbursement(
    disbursement_id: uuid.UUID,
    db:              DbDep,
    token:           PlatformAdminDep,
) -> dict:
    d = await _get_or_404(disbursement_id, db)

    if d.status != DisbursementStatus.PENDING.value:
        raise HTTPException(
            status_code=409,
            detail={
                "error":  "CANNOT_CANCEL",
                "detail": f"Disbursement is already in '{d.status}' state. "
                          "Only PENDING disbursements can be cancelled.",
            },
        )

    d.status       = DisbursementStatus.CANCELLED.value
    d.completed_at = datetime.now(timezone.utc)
    db.add(d)
    await db.commit()
    return {"message": "Disbursement cancelled.", "id": str(d.id), "status": "cancelled"}

"""
api/v1/verification.py — Organisation verification (payment + KYC badge)
═══════════════════════════════════════════════════════════════════════════════

Two independent verification tracks:

  TRACK 1 — Payment Verification (automatic)
    Set by subscription_service the moment an org's subscription becomes active.
    Means: "this org has an active paid plan."
    Controls: full access to plan features.

  TRACK 2 — KYC Verification (manual, admin-vetted)
    Org submits business registration documents.
    Platform admin reviews and approves/rejects.
    On approval: is_kyc_verified = True → "Verified" badge shown on frontend.

Endpoints
─────────
  Org-facing
    GET  /orgs/my/verification              — own verification status (both tracks)
    POST /orgs/my/kyc/submit                — create KYC submission + attach documents
    POST /orgs/my/kyc/documents             — add a document to pending submission
    GET  /orgs/my/kyc                       — check KYC submission status

  Public
    GET  /orgs/{slug}/badge                 — public verification badge (slug lookup)

  Internal (service-to-service)
    POST /internal/orgs/{org_id}/set-payment-verified   — auto-called by subscription_service

  Admin
    GET  /admin/kyc/pending                 — queue of pending/under_review submissions
    GET  /admin/kyc/{submission_id}         — full submission detail with documents
    POST /admin/kyc/{submission_id}/review  — approve / reject / request-more-info
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, UploadFile
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from db.session import get_async_session as get_db
from models.organisation import (
    KYCDocumentType, KYCStatus, Organisation,
    OrgKYCDocument, OrgKYCSubmission,
)

log = structlog.get_logger(__name__)
router = APIRouter(tags=["Verification"])

_SERVICE_KEY = getattr(settings, "INTERNAL_SERVICE_KEY", "change-me-in-env")


# ── Auth helpers ──────────────────────────────────────────────────────────────

def _require_service_key(x_service_key: str = Header(..., alias="X-Service-Key")) -> None:
    if x_service_key != _SERVICE_KEY:
        raise HTTPException(401, {"error": "INVALID_SERVICE_KEY"})


def _decode_jwt(authorization: str = Header(default="")) -> dict:
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(401, {"error": "UNAUTHORISED", "message": "Bearer token required."})
    import jwt as _jwt
    try:
        claims = _jwt.decode(
            authorization[7:],
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_aud": False},
        )
        return claims
    except Exception:
        raise HTTPException(401, {"error": "UNAUTHORISED", "message": "Invalid or expired token."})


def _require_admin(authorization: str = Header(default="")) -> dict:
    claims = _decode_jwt(authorization)
    role = claims.get("org_role", "")
    platform_role = claims.get("platform_role", "")
    if role not in ("OWNER", "ADMIN") and platform_role not in ("super_admin", "admin"):
        raise HTTPException(403, {"error": "FORBIDDEN", "message": "Admin access required."})
    return claims


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ── Serialisers ───────────────────────────────────────────────────────────────

def _org_verification_out(org: Organisation) -> dict:
    return {
        "org_id":              str(org.id),
        "slug":                org.slug,
        "display_name":        org.display_name,
        "is_payment_verified": org.is_payment_verified,
        "payment_verified_at": org.payment_verified_at.isoformat() if org.payment_verified_at else None,
        "is_kyc_verified":     org.is_kyc_verified,
        "kyc_verified_at":     org.kyc_verified_at.isoformat() if org.kyc_verified_at else None,
        "kyc_rejection_reason": org.kyc_rejection_reason,
        "verification_level":  _verification_level(org),
    }


def _verification_level(org: Organisation) -> str:
    if org.is_kyc_verified:
        return "kyc_verified"
    if org.is_payment_verified:
        return "payment_verified"
    return "unverified"


def _submission_out(sub: OrgKYCSubmission, docs: list[OrgKYCDocument] | None = None) -> dict:
    d = {
        "id":             str(sub.id),
        "org_id":         str(sub.org_id),
        "status":         sub.status,
        "business_type":  sub.business_type,
        "reg_number":     sub.reg_number,
        "tax_id":         sub.tax_id,
        "notes_for_admin": sub.notes_for_admin,
        "rejection_reason": sub.rejection_reason,
        "submitted_at":   sub.submitted_at.isoformat(),
        "reviewed_at":    sub.reviewed_at.isoformat() if sub.reviewed_at else None,
        "updated_at":     sub.updated_at.isoformat(),
    }
    if docs is not None:
        d["documents"] = [_doc_out(doc) for doc in docs]
    return d


def _doc_out(doc: OrgKYCDocument) -> dict:
    return {
        "id":            str(doc.id),
        "document_type": doc.document_type,
        "file_url":      doc.file_url,
        "file_name":     doc.file_name,
        "file_size_bytes": doc.file_size_bytes,
        "is_verified":   doc.is_verified,
        "uploaded_at":   doc.uploaded_at.isoformat(),
    }


async def _get_org_for_user(claims: dict, db: AsyncSession) -> Organisation:
    org_id = claims.get("org_id")
    if not org_id:
        raise HTTPException(400, {"error": "NO_ORG", "message": "No active organisation in token."})
    org = await db.get(Organisation, uuid.UUID(org_id))
    if not org:
        raise HTTPException(404, {"error": "NOT_FOUND", "message": "Organisation not found."})
    return org


# ══════════════════════════════════════════════════════════════════════════════
# ORG-FACING
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/orgs/my/verification", summary="Get my organisation's verification status")
async def my_verification_status(
    claims: dict = Depends(_decode_jwt),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Returns both verification tracks for the authenticated organisation:
    - payment_verified: auto-set when subscription becomes active
    - kyc_verified: set by platform admin after KYC document review

    Also returns the latest KYC submission status if one exists.
    """
    org = await _get_org_for_user(claims, db)
    out = _org_verification_out(org)

    # Attach latest submission summary
    latest_sub = (await db.execute(
        select(OrgKYCSubmission)
        .where(OrgKYCSubmission.org_id == org.id)
        .order_by(OrgKYCSubmission.submitted_at.desc())
        .limit(1)
    )).scalar_one_or_none()

    out["kyc_submission"] = _submission_out(latest_sub) if latest_sub else None
    return out


@router.post("/orgs/my/kyc/submit", summary="Submit KYC documents for manual verification", status_code=201)
async def submit_kyc(
    body: dict,
    claims: dict = Depends(_decode_jwt),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Create a new KYC submission. Attach document URLs pointing to files already
    uploaded to MinIO (/riviwa-kyc/{org_id}/...).

    Body:
    {
      "business_type":   "BUSINESS",           // optional context
      "reg_number":      "TZ-2024-12345",
      "tax_id":          "TIN-123456789",
      "notes_for_admin": "Please review urgently — we have a government tender deadline.",
      "documents": [
        {
          "document_type": "business_license",
          "file_url":      "https://minio.riviwa.com/reviwa-kyc/uuid/business_license.pdf",
          "file_name":     "business_license.pdf",
          "file_size_bytes": 245760
        },
        {
          "document_type": "certificate_of_incorporation",
          "file_url":      "https://minio.riviwa.com/reviwa-kyc/uuid/cert_of_inc.pdf",
          "file_name":     "cert_of_inc.pdf"
        }
      ]
    }

    Valid document_type values:
      business_license, certificate_of_incorporation, tax_clearance, tax_id,
      directors_national_id, utility_bill, bank_statement,
      memorandum_of_association, audited_accounts, other
    """
    org = await _get_org_for_user(claims, db)
    user_id = claims.get("sub")

    # Block if an active submission already exists
    active_sub = (await db.execute(
        select(OrgKYCSubmission).where(
            OrgKYCSubmission.org_id == org.id,
            OrgKYCSubmission.status.in_([KYCStatus.PENDING.value, KYCStatus.UNDER_REVIEW.value, KYCStatus.MORE_INFO.value]),
        )
    )).scalar_one_or_none()

    if active_sub and active_sub.status == KYCStatus.UNDER_REVIEW.value:
        raise HTTPException(409, {
            "error": "SUBMISSION_UNDER_REVIEW",
            "message": "Your KYC submission is currently being reviewed. Please wait for the outcome.",
            "submission_id": str(active_sub.id),
        })

    # If a pending/more_info submission exists, re-open it (add documents)
    if active_sub:
        submission = active_sub
        submission.notes_for_admin = body.get("notes_for_admin", submission.notes_for_admin)
        submission.status = KYCStatus.PENDING.value
        submission.updated_at = _utcnow()
    else:
        submission = OrgKYCSubmission(
            org_id=org.id,
            submitted_by_id=uuid.UUID(user_id) if user_id else org.id,
            status=KYCStatus.PENDING.value,
            business_type=body.get("business_type"),
            reg_number=body.get("reg_number"),
            tax_id=body.get("tax_id"),
            notes_for_admin=body.get("notes_for_admin"),
        )
        db.add(submission)
        await db.flush()

    # Attach documents
    docs = []
    for item in body.get("documents", []):
        doc_type = item.get("document_type", KYCDocumentType.OTHER.value)
        file_url = item.get("file_url", "").strip()
        if not file_url:
            continue
        doc = OrgKYCDocument(
            org_id=org.id,
            submission_id=submission.id,
            document_type=doc_type,
            file_url=file_url,
            file_name=item.get("file_name"),
            file_size_bytes=item.get("file_size_bytes"),
            uploaded_by_id=uuid.UUID(user_id) if user_id else org.id,
        )
        db.add(doc)
        docs.append(doc)

    await db.flush()
    await db.commit()

    log.info("kyc.submission_created", org_id=str(org.id), submission_id=str(submission.id),
             doc_count=len(docs))

    return {
        "message": "KYC submission received. Our team will review within 2–3 business days.",
        "submission": _submission_out(submission, docs),
    }


@router.post("/orgs/my/kyc/documents", summary="Add a document to an existing KYC submission", status_code=201)
async def add_kyc_document(
    body: dict,
    claims: dict = Depends(_decode_jwt),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Attach one additional document to the current pending/more_info submission.
    Use this when an admin has requested more information.

    Body:
    {
      "document_type": "utility_bill",
      "file_url":      "https://minio.riviwa.com/reviwa-kyc/.../utility_bill.pdf",
      "file_name":     "utility_bill.pdf",
      "file_size_bytes": 102400
    }
    """
    org = await _get_org_for_user(claims, db)
    user_id = claims.get("sub")

    sub = (await db.execute(
        select(OrgKYCSubmission).where(
            OrgKYCSubmission.org_id == org.id,
            OrgKYCSubmission.status.in_([
                KYCStatus.PENDING.value, KYCStatus.MORE_INFO.value
            ]),
        ).order_by(OrgKYCSubmission.submitted_at.desc()).limit(1)
    )).scalar_one_or_none()

    if not sub:
        raise HTTPException(404, {
            "error": "NO_ACTIVE_SUBMISSION",
            "message": "No pending submission found. Use POST /orgs/my/kyc/submit first.",
        })

    file_url = body.get("file_url", "").strip()
    if not file_url:
        raise HTTPException(422, {"error": "VALIDATION_ERROR", "message": "file_url is required."})

    doc = OrgKYCDocument(
        org_id=org.id,
        submission_id=sub.id,
        document_type=body.get("document_type", KYCDocumentType.OTHER.value),
        file_url=file_url,
        file_name=body.get("file_name"),
        file_size_bytes=body.get("file_size_bytes"),
        uploaded_by_id=uuid.UUID(user_id) if user_id else org.id,
    )
    db.add(doc)
    if sub.status == KYCStatus.MORE_INFO.value:
        sub.status = KYCStatus.PENDING.value
        sub.updated_at = _utcnow()
    await db.commit()
    await db.refresh(doc)

    return {"message": "Document added.", "document": _doc_out(doc)}


@router.get("/orgs/my/kyc", summary="Get my organisation's KYC submission status")
async def my_kyc_status(
    claims: dict = Depends(_decode_jwt),
    db: AsyncSession = Depends(get_db),
) -> dict:
    org = await _get_org_for_user(claims, db)

    submissions = (await db.execute(
        select(OrgKYCSubmission)
        .where(OrgKYCSubmission.org_id == org.id)
        .order_by(OrgKYCSubmission.submitted_at.desc())
        .limit(5)
    )).scalars().all()

    result = []
    for sub in submissions:
        docs = (await db.execute(
            select(OrgKYCDocument)
            .where(OrgKYCDocument.submission_id == sub.id)
            .order_by(OrgKYCDocument.uploaded_at)
        )).scalars().all()
        result.append(_submission_out(sub, list(docs)))

    return {
        "org_id":       str(org.id),
        "is_kyc_verified": org.is_kyc_verified,
        "kyc_verified_at": org.kyc_verified_at.isoformat() if org.kyc_verified_at else None,
        "submissions":  result,
    }


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/orgs/{slug}/badge", summary="Public: get verification badge for an organisation")
async def public_org_badge(slug: str, db: AsyncSession = Depends(get_db)) -> dict:
    """
    Used by the frontend to show verification badges on public org profiles,
    product listings, and search results.

    Returns only non-sensitive verification data — no document URLs or KYC details.
    """
    org = (await db.execute(
        select(Organisation).where(Organisation.slug == slug)
    )).scalar_one_or_none()

    if not org:
        raise HTTPException(404, {"error": "NOT_FOUND", "message": "Organisation not found."})

    return {
        "org_id":              str(org.id),
        "slug":                org.slug,
        "display_name":        org.display_name,
        "logo_url":            org.logo_url,
        "is_payment_verified": org.is_payment_verified,
        "is_kyc_verified":     org.is_kyc_verified,
        "kyc_verified_at":     org.kyc_verified_at.isoformat() if org.kyc_verified_at else None,
        "verification_level":  _verification_level(org),
        "badge": {
            "show_payment_badge": org.is_payment_verified,
            "show_kyc_badge":     org.is_kyc_verified,
            "label": (
                "Verified Business" if org.is_kyc_verified
                else "Active Subscriber" if org.is_payment_verified
                else None
            ),
            "color": (
                "blue"   if org.is_kyc_verified
                else "green" if org.is_payment_verified
                else None
            ),
        },
    }


# ══════════════════════════════════════════════════════════════════════════════
# INTERNAL (service-to-service)
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/internal/orgs/{org_id}/set-payment-verified",
    summary="[Internal] Mark org as payment-verified when subscription activates",
    dependencies=[Depends(_require_service_key)],
    include_in_schema=False,
)
async def set_payment_verified(
    org_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Called by subscription_service after a subscription becomes active.
    Sets is_payment_verified = True and records the timestamp.
    Idempotent — safe to call multiple times.
    """
    org = await db.get(Organisation, org_id)
    if not org:
        raise HTTPException(404, {"error": "NOT_FOUND"})

    if not org.is_payment_verified:
        org.is_payment_verified = True
        org.payment_verified_at = _utcnow()
        # Also activate org status if still pending
        if org.status.value == "PENDING_VERIFICATION":
            org.status = "ACTIVE"
        await db.commit()
        log.info("org.payment_verified", org_id=str(org_id))

    return {
        "ok": True,
        "org_id": str(org_id),
        "is_payment_verified": org.is_payment_verified,
        "payment_verified_at": org.payment_verified_at.isoformat() if org.payment_verified_at else None,
    }


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/admin/kyc/pending", summary="Admin: list KYC submissions awaiting review")
async def admin_kyc_queue(
    status: Optional[str] = Query(default=None, description="Filter: pending|under_review|more_info|approved|rejected"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    claims: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Returns KYC submissions sorted by submission date (oldest first — work the queue in order).
    Default filter: pending + under_review + more_info (actionable items only).
    """
    q = select(OrgKYCSubmission)
    if status:
        q = q.where(OrgKYCSubmission.status == status)
    else:
        q = q.where(OrgKYCSubmission.status.in_([
            KYCStatus.PENDING.value, KYCStatus.UNDER_REVIEW.value, KYCStatus.MORE_INFO.value
        ]))

    total = (await db.execute(
        select(func.count()).select_from(q.subquery())
    )).scalar_one()

    submissions = (await db.execute(
        q.order_by(OrgKYCSubmission.submitted_at.asc())
        .offset((page - 1) * size).limit(size)
    )).scalars().all()

    result = []
    for sub in submissions:
        org = await db.get(Organisation, sub.org_id)
        doc_count = (await db.execute(
            select(func.count()).where(OrgKYCDocument.submission_id == sub.id)
        )).scalar_one()
        entry = _submission_out(sub)
        entry["org"] = {
            "display_name": org.display_name if org else "?",
            "slug":         org.slug if org else "?",
            "org_type":     org.org_type.value if org else "?",
            "country_code": org.country_code if org else "?",
        }
        entry["document_count"] = doc_count
        result.append(entry)

    return {
        "total": total, "page": page, "size": size,
        "submissions": result,
    }


@router.get("/admin/kyc/{submission_id}", summary="Admin: view full KYC submission with documents")
async def admin_kyc_detail(
    submission_id: uuid.UUID,
    claims: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    sub = await db.get(OrgKYCSubmission, submission_id)
    if not sub:
        raise HTTPException(404, {"error": "NOT_FOUND"})

    # Mark as under_review when admin opens it
    if sub.status == KYCStatus.PENDING.value:
        sub.status = KYCStatus.UNDER_REVIEW.value
        sub.updated_at = _utcnow()
        await db.commit()

    docs = (await db.execute(
        select(OrgKYCDocument)
        .where(OrgKYCDocument.submission_id == submission_id)
        .order_by(OrgKYCDocument.uploaded_at)
    )).scalars().all()

    org = await db.get(Organisation, sub.org_id)
    result = _submission_out(sub, list(docs))
    result["org"] = {
        "id":              str(org.id) if org else None,
        "display_name":    org.display_name if org else None,
        "legal_name":      org.legal_name if org else None,
        "slug":            org.slug if org else None,
        "org_type":        org.org_type.value if org else None,
        "country_code":    org.country_code if org else None,
        "registration_number": org.registration_number if org else None,
        "tax_id":          org.tax_id if org else None,
        "support_email":   org.support_email if org else None,
        "is_payment_verified": org.is_payment_verified if org else False,
        "is_kyc_verified": org.is_kyc_verified if org else False,
    }
    return result


@router.post("/admin/kyc/{submission_id}/review", summary="Admin: approve, reject, or request more info")
async def admin_kyc_review(
    submission_id: uuid.UUID,
    body: dict,
    claims: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Body:
    {
      "action":           "approve" | "reject" | "more_info",
      "rejection_reason": "Missing tax clearance certificate",   // required for reject
      "admin_notes":      "Approved — all 3 docs verified",      // optional internal note
      "more_info_request": "Please provide a utility bill dated within 3 months."  // for more_info
    }
    """
    sub = await db.get(OrgKYCSubmission, submission_id)
    if not sub:
        raise HTTPException(404, {"error": "NOT_FOUND", "message": "Submission not found."})
    if sub.status == KYCStatus.APPROVED.value:
        raise HTTPException(409, {"error": "ALREADY_APPROVED", "message": "Submission already approved."})

    action = body.get("action", "").lower()
    if action not in ("approve", "reject", "more_info"):
        raise HTTPException(422, {"error": "VALIDATION_ERROR",
                                  "message": "action must be approve, reject, or more_info."})

    admin_id = claims.get("sub")
    now = _utcnow()
    org = await db.get(Organisation, sub.org_id)

    if action == "approve":
        sub.status = KYCStatus.APPROVED.value
        sub.reviewed_by_id = uuid.UUID(admin_id) if admin_id else None
        sub.reviewed_at = now
        sub.admin_notes = body.get("admin_notes")
        sub.rejection_reason = None
        sub.updated_at = now

        if org:
            org.is_kyc_verified = True
            org.kyc_verified_at = now
            org.kyc_verified_by_id = uuid.UUID(admin_id) if admin_id else None
            org.kyc_rejection_reason = None
            # Also activate is_verified (legacy flag)
            org.is_verified = True
            org.verified_at = now
            org.verified_by_id = uuid.UUID(admin_id) if admin_id else None

        await db.commit()
        log.info("kyc.approved", submission_id=str(submission_id), org_id=str(sub.org_id),
                 admin_id=admin_id)
        return {
            "message": f"KYC approved. Organisation '{org.display_name if org else sub.org_id}' is now KYC-verified.",
            "submission": _submission_out(sub),
            "org_verification": _org_verification_out(org) if org else None,
        }

    elif action == "reject":
        reason = body.get("rejection_reason", "").strip()
        if not reason:
            raise HTTPException(422, {"error": "VALIDATION_ERROR",
                                      "message": "rejection_reason is required when action=reject."})
        sub.status = KYCStatus.REJECTED.value
        sub.reviewed_by_id = uuid.UUID(admin_id) if admin_id else None
        sub.reviewed_at = now
        sub.rejection_reason = reason
        sub.admin_notes = body.get("admin_notes")
        sub.updated_at = now

        if org:
            org.kyc_rejection_reason = reason

        await db.commit()
        log.info("kyc.rejected", submission_id=str(submission_id), reason=reason)
        return {
            "message": "KYC rejected. Organisation notified.",
            "submission": _submission_out(sub),
        }

    else:  # more_info
        request_text = body.get("more_info_request", body.get("rejection_reason", "")).strip()
        if not request_text:
            raise HTTPException(422, {"error": "VALIDATION_ERROR",
                                      "message": "more_info_request is required when action=more_info."})
        sub.status = KYCStatus.MORE_INFO.value
        sub.reviewed_by_id = uuid.UUID(admin_id) if admin_id else None
        sub.rejection_reason = request_text
        sub.admin_notes = body.get("admin_notes")
        sub.updated_at = now

        await db.commit()
        return {
            "message": "More information requested. Organisation can re-submit.",
            "submission": _submission_out(sub),
            "request": request_text,
        }


@router.patch("/admin/orgs/{org_id}/payment-verification", summary="Admin: manually set payment verification")
async def admin_set_payment_verification(
    org_id: uuid.UUID,
    body: dict,
    claims: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Manually grant or revoke payment verification for an org.
    Used for bank transfer confirmations or manual overrides.

    Body: { "is_payment_verified": true | false }
    """
    org = await db.get(Organisation, org_id)
    if not org:
        raise HTTPException(404, {"error": "NOT_FOUND"})

    org.is_payment_verified = bool(body.get("is_payment_verified", True))
    if org.is_payment_verified and not org.payment_verified_at:
        org.payment_verified_at = _utcnow()
    await db.commit()

    return {
        "message": f"Payment verification set to {org.is_payment_verified}.",
        "org_verification": _org_verification_out(org),
    }


# ══════════════════════════════════════════════════════════════════════════════
# FILE UPLOAD — multipart upload directly to MinIO
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/orgs/my/kyc/documents/upload",
    summary="Upload a KYC document file (multipart) — stores to MinIO, creates document record",
    status_code=201,
)
async def upload_kyc_document(
    file: UploadFile = File(..., description="PDF, JPEG, PNG, or DOCX — max 15 MB"),
    document_type: str = Form(
        ...,
        description=(
            "business_license | certificate_of_incorporation | tax_clearance | tax_id | "
            "directors_national_id | utility_bill | bank_statement | "
            "memorandum_of_association | audited_accounts | other"
        ),
    ),
    claims: dict = Depends(_decode_jwt),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Upload a document file for the current pending KYC submission.
    The file is stored in MinIO at:
      `reviwa-kyc/kyc/{org_id}/{submission_id}/{document_type}_{short_id}.{ext}`

    A KYC submission must already exist (call `POST /orgs/my/kyc/submit` first).
    If the submission is in `more_info` status, uploading a file moves it back to `pending`.

    Returns the document record with the stored `file_url`.
    """
    from core.config import settings as cfg
    from services.kyc_document_service import KYCDocumentService, KYCUploadError

    org = await _get_org_for_user(claims, db)
    user_id = claims.get("sub")

    sub = (await db.execute(
        select(OrgKYCSubmission).where(
            OrgKYCSubmission.org_id == org.id,
            OrgKYCSubmission.status.in_([
                KYCStatus.PENDING.value, KYCStatus.MORE_INFO.value,
            ]),
        ).order_by(OrgKYCSubmission.submitted_at.desc()).limit(1)
    )).scalar_one_or_none()

    if not sub:
        raise HTTPException(404, {
            "error": "NO_ACTIVE_SUBMISSION",
            "message": (
                "No pending submission to attach this document to. "
                "Create a submission first: POST /orgs/my/kyc/submit"
            ),
        })

    try:
        svc = KYCDocumentService(cfg)
        file_url, file_name, file_size = await svc.upload(
            file=file,
            org_id=org.id,
            submission_id=sub.id,
            document_type=document_type,
        )
    except KYCUploadError as exc:
        raise HTTPException(422, {"error": "UPLOAD_ERROR", "message": str(exc)})

    doc = OrgKYCDocument(
        org_id=org.id,
        submission_id=sub.id,
        document_type=document_type,
        file_url=file_url,
        file_name=file_name,
        file_size_bytes=file_size,
        uploaded_by_id=uuid.UUID(user_id) if user_id else org.id,
    )
    db.add(doc)

    if sub.status == KYCStatus.MORE_INFO.value:
        sub.status = KYCStatus.PENDING.value
        sub.updated_at = _utcnow()

    await db.commit()
    await db.refresh(doc)

    log.info("kyc.document_uploaded",
             org_id=str(org.id), submission_id=str(sub.id),
             doc_type=document_type, size_bytes=file_size)

    return {
        "message":  f"Document '{file_name}' uploaded successfully.",
        "document": _doc_out(doc),
        "submission_status": sub.status,
    }


@router.delete(
    "/orgs/my/kyc/documents/{doc_id}",
    summary="Remove a document from a pending KYC submission",
)
async def delete_kyc_document(
    doc_id: uuid.UUID,
    claims: dict = Depends(_decode_jwt),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Remove a document from the current pending or more_info KYC submission.
    The file is also deleted from MinIO.
    Documents cannot be removed from submissions that are under_review or approved.
    """
    from core.config import settings as cfg
    from services.kyc_document_service import KYCDocumentService

    org = await _get_org_for_user(claims, db)

    doc = await db.get(OrgKYCDocument, doc_id)
    if not doc or str(doc.org_id) != str(org.id):
        raise HTTPException(404, {"error": "NOT_FOUND", "message": "Document not found."})

    sub = await db.get(OrgKYCSubmission, doc.submission_id)
    if sub and sub.status not in (KYCStatus.PENDING.value, KYCStatus.MORE_INFO.value):
        raise HTTPException(409, {
            "error": "SUBMISSION_NOT_EDITABLE",
            "message": (
                f"Cannot remove documents — submission is '{sub.status}'. "
                "Only pending or more_info submissions can be edited."
            ),
        })

    svc = KYCDocumentService(cfg)
    await svc.delete(doc.file_url)
    await db.delete(doc)
    await db.commit()

    log.info("kyc.document_deleted", org_id=str(org.id), doc_id=str(doc_id))

    return {"message": f"Document '{doc.file_name or doc_id}' removed.", "id": str(doc_id)}

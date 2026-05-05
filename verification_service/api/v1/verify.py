"""api/v1/verify.py — Core verification and fake report endpoints."""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional

import httpx
import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from db.session import get_async_session
from models.verification import (
    FakeSuspectReport, ReportStatus, UnrecognizedScanHeatmap,
    VerificationEvent, VerificationResult,
)
from services.image_intelligence_client import analyze_fake_image
from services.verify_service import compute_geohash, fetch_product_details, resolve_code

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/verify", tags=["Verification"])


@router.post("", status_code=200)
async def verify_code(body: dict, db: AsyncSession = Depends(get_async_session)) -> dict:
    """
    Verify a QR code or SMS short code.

    A QR / unique code is PERMANENT evidence that a person used a service.
    It is only marked as ALREADY_USED when feedback has actually been submitted through it.

    Results:
      AUTHENTIC     — Code is genuine and feedback has NOT yet been submitted.
                      Consumer can now leave feedback.
      ALREADY_USED  — Feedback was submitted through this code.
                      Shows the service/transaction details as proof of service.
      UNRECOGNIZED  — Code not found. Prompt user to report as suspected fake.
    """
    raw_code = body.get("code", "").strip()
    if not raw_code:
        raise HTTPException(status_code=422, detail={"error": "CODE_REQUIRED"})

    # Extract short_code from full QR URL if needed
    if "/qr/" in raw_code:
        raw_code = raw_code.split("/qr/")[-1].split("?")[0]

    lat = body.get("lat")
    lng = body.get("lng")
    user_agent = body.get("user_agent", "")

    qr_data, clean_code = await resolve_code(raw_code)

    if not qr_data:
        event = VerificationEvent(
            short_code=clean_code[:130],
            result=VerificationResult.UNRECOGNIZED.value,
            scanner_lat=float(lat) if lat else None,
            scanner_lng=float(lng) if lng else None,
            user_agent=user_agent[:512] if user_agent else None,
        )
        db.add(event)
        if lat and lng:
            db.add(UnrecognizedScanHeatmap(
                verification_event_id=event.id, lat=float(lat), lng=float(lng),
                cluster_cell=compute_geohash(float(lat), float(lng)),
            ))
        await db.commit()
        return {
            "result": "UNRECOGNIZED",
            "verification_event_id": str(event.id),
            "message": "This code was not found in the Riviwa system. If you believe this is a genuine product or service, please report it.",
            "actions": ["report_fake"],
        }

    product_details = None
    if qr_data.get("product_id"):
        product_details = await fetch_product_details(qr_data["product_id"])

    qr_type = qr_data.get("qr_type", "")

    if qr_data.get("feedback_already_submitted"):
        # Code was used — feedback was submitted. Show service details as proof.
        result = VerificationResult.ALREADY_USED
        if qr_type == "PRODUCT":
            message = "This product has already been verified and feedback submitted. This is a genuine product — see details below."
        elif qr_type == "RECEIPT":
            message = "Feedback has already been submitted for this transaction. This is your permanent proof of service."
        else:
            message = "Feedback has already been submitted using this code. This is your permanent proof of service."
    else:
        result = VerificationResult.AUTHENTIC
        if qr_type == "PRODUCT":
            message = "This is a genuine Riviwa-verified product. You can now leave feedback about your experience."
        elif qr_type == "RECEIPT":
            message = "Receipt verified. This is a genuine service transaction. You can now leave your feedback."
        elif qr_type in ("LOCATION", "SERVICE"):
            message = "Verified. This is a registered Riviwa service point. You can now leave feedback."
        else:
            message = "Verified. This is a genuine Riviwa-registered entity. You can now leave feedback."

    event = VerificationEvent(
        short_code=clean_code[:130],
        result=result.value,
        product_id=uuid.UUID(qr_data["product_id"]) if qr_data.get("product_id") else None,
        organisation_id=uuid.UUID(qr_data["organisation_id"]) if qr_data.get("organisation_id") else None,
        qr_code_id=uuid.UUID(qr_data["qr_code_id"]) if qr_data.get("qr_code_id") else None,
        qr_type=qr_type,
        scanner_lat=float(lat) if lat else None,
        scanner_lng=float(lng) if lng else None,
        user_agent=user_agent[:512] if user_agent else None,
        feedback_id=uuid.UUID(qr_data["feedback_id"]) if qr_data.get("feedback_id") else None,
        product_details=product_details,
    )
    db.add(event)
    await db.commit()

    response = {
        "result": result.value,
        "verification_event_id": str(event.id),
        "message": message,
        "short_code": qr_data.get("short_code"),
        "sms_code": qr_data.get("sms_code"),
        "qr_type": qr_type,
        "organisation_id": qr_data.get("organisation_id"),
        "scan_count": qr_data.get("scan_count", 0),
    }

    if product_details:
        response["product"] = product_details

    if result == VerificationResult.AUTHENTIC:
        response["redirect_url"] = qr_data.get("redirect_url")
        response["actions"] = ["submit_feedback"]
    elif result == VerificationResult.ALREADY_USED:
        response["feedback_id"] = str(event.feedback_id) if event.feedback_id else None
        response["actions"] = ["track_feedback", "view_service_details"]
        # Fetch service context so consumer can see which service they used
        if qr_data.get("receipt_session_id"):
            service_ctx = await _fetch_receipt_context(qr_data["receipt_session_id"])
            if service_ctx:
                response["service_context"] = service_ctx
                response["note"] = "This QR code is permanent evidence that you used this service."

    return response


@router.post("/report-fake", status_code=status.HTTP_201_CREATED)
async def report_fake_product(
    verification_event_id: str = Form(...),
    reporter_phone: Optional[str] = Form(default=None),
    reporter_name: Optional[str] = Form(default=None),
    description: Optional[str] = Form(default=None),
    gps_lat: Optional[float] = Form(default=None),
    gps_lng: Optional[float] = Form(default=None),
    location_description: Optional[str] = Form(default=None),
    photo: Optional[UploadFile] = File(default=None),
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """
    Report a suspected fake/counterfeit product or service.

    If a photo is provided:
      1. Upload to MinIO (permanent storage for field agents).
      2. Send to ai_service: CLIP ViT-B/32 similarity search (org-scoped → platform-wide)
         then Llama 4 Scout visual reasoning about counterfeit indicators.
      3. Store the AI verdict in ai_analysis — returned immediately to the consumer.
    """
    event_id = uuid.UUID(verification_event_id)
    event = await db.get(VerificationEvent, event_id)
    if not event:
        raise HTTPException(status_code=404, detail={"error": "VERIFICATION_EVENT_NOT_FOUND"})

    photo_key = photo_url = None
    photo_bytes: Optional[bytes] = None

    if photo and photo.size:
        photo_bytes = await photo.read()
        photo_key, photo_url = await _upload_fake_photo_bytes(
            photo_bytes, photo.filename or "photo.jpg",
            photo.content_type or "image/jpeg", str(event_id),
        )

    # Run AI image analysis if a photo was submitted
    ai_analysis: Optional[dict] = None
    if photo_bytes:
        org_id = str(event.organisation_id) if event.organisation_id else None
        location_ctx = location_description or (
            f"{gps_lat},{gps_lng}" if gps_lat and gps_lng else None
        )
        ai_analysis = await analyze_fake_image(
            photo_bytes,
            org_id=org_id,
            short_code=event.short_code,
            location=location_ctx,
        )
        if ai_analysis:
            log.info("fake_report.ai_analysis_done",
                     verdict=ai_analysis.get("ai_verdict", {}).get("verdict"),
                     similarity=ai_analysis.get("clip_similarity", 0))
        else:
            log.warning("fake_report.ai_analysis_unavailable")

    report = FakeSuspectReport(
        verification_event_id=event_id,
        short_code_scanned=event.short_code,
        reporter_phone=reporter_phone,
        reporter_name=reporter_name,
        description=description,
        photo_key=photo_key,
        photo_url=photo_url,
        gps_lat=gps_lat,
        gps_lng=gps_lng,
        location_description=location_description,
        status=ReportStatus.SUBMITTED.value,
        organisation_id=event.organisation_id,
        ai_analysis=ai_analysis,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    log.info("fake_report.submitted", report_id=str(report.id),
             lat=gps_lat, lng=gps_lng, has_photo=bool(photo_key),
             ai_verdict=ai_analysis.get("ai_verdict", {}).get("verdict") if ai_analysis else None)

    response = {
        "report_id": str(report.id),
        "status": "SUBMITTED",
        "message": "Thank you for reporting. Our field team will investigate this location.",
        "has_photo": bool(photo_key),
        "location": {"lat": gps_lat, "lng": gps_lng, "description": location_description},
    }

    if ai_analysis:
        verdict = ai_analysis.get("ai_verdict", {})
        response["ai_analysis"] = {
            "verdict":            verdict.get("verdict"),
            "confidence":         verdict.get("confidence"),
            "suspected_brand":    verdict.get("suspected_brand"),
            "suspected_product":  verdict.get("suspected_product"),
            "clip_similarity":    ai_analysis.get("clip_similarity"),
            "top_matches":        ai_analysis.get("top_matches", [])[:3],
            "counterfeit_indicators": verdict.get("counterfeit_indicators", []),
            "reasoning":          verdict.get("reasoning"),
            "recommended_action": verdict.get("recommended_action"),
        }

    return response


async def _fetch_receipt_context(receipt_session_id: str) -> Optional[dict]:
    """
    Fetch receipt/service context from qr_service when a code is ALREADY_USED.
    Returns the service details (attendant, location, date, amount etc.) so the
    consumer can see which service they used — permanent evidence of service.
    """
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.get(
                f"{settings.QR_SERVICE_URL}/api/v1/internal/qr/receipt-session/{receipt_session_id}",
                headers={"X-Service-Key": settings.INTERNAL_SERVICE_KEY},
            )
            if resp.status_code == 200:
                data = resp.json()
                return {k: data[k] for k in [
                    "service_name", "department", "attendant_name",
                    "location", "transaction_datetime", "receipt_number",
                    "amount", "currency", "custom_attributes",
                ] if k in data and data[k] is not None}
    except Exception as exc:
        log.warning("verify.receipt_context_fetch_failed", session_id=receipt_session_id, error=str(exc))
    return None


async def _upload_fake_photo_bytes(
    data: bytes, filename: str, content_type: str, event_id: str
) -> tuple:
    import aiobotocore.session as aio_session
    bucket = settings.VERIFICATION_BUCKET
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    ext = filename.rsplit(".", 1)[-1][:10]
    key = f"fake-reports/{event_id}/{ts}.{ext}"
    sess = aio_session.get_session()
    async with sess.create_client(
        "s3", endpoint_url=settings.MINIO_ENDPOINT,
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
    ) as client:
        try:
            await client.head_bucket(Bucket=bucket)
        except Exception:
            await client.create_bucket(Bucket=bucket)
        await client.put_object(Bucket=bucket, Key=key, Body=data, ContentType=content_type)
        url = await client.generate_presigned_url(
            "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=86400 * 365)
    return key, url

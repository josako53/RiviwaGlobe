"""api/v1/activities.py — HTTP orchestration only"""
from __future__ import annotations
import uuid
from typing import Any, Dict, Optional
from fastapi import APIRouter, File, Form, Query, UploadFile, status
from core.dependencies import DbDep, KafkaDep, StaffDep
from services.activity_service import ActivityService

router = APIRouter(prefix="/activities", tags=["Engagement Activities"])

def _svc(db, kafka): return ActivityService(db=db, producer=kafka)
def _a_out(a): return {
    "id":str(a.id),
    "project_id":str(a.project_id),
    "stage_id":str(a.stage_id) if a.stage_id else None,
    "subproject_id":str(a.subproject_id) if a.subproject_id else None,
    "stage":a.stage,"activity_type":a.activity_type,"status":a.status,
    "title":a.title,"description":a.description,"agenda":a.agenda,
    "venue":a.venue,"lga":a.lga,"ward":a.ward,
    "gps_lat":a.gps_lat,"gps_lng":a.gps_lng,
    "virtual_platform":a.virtual_platform,"virtual_url":a.virtual_url,
    "virtual_meeting_id":a.virtual_meeting_id,
    "scheduled_at":a.scheduled_at.isoformat() if a.scheduled_at else None,
    "conducted_at":a.conducted_at.isoformat() if a.conducted_at else None,
    "duration_hours":a.duration_hours,
    "expected_count":a.expected_count,"actual_count":a.actual_count,
    "female_count":a.female_count,"vulnerable_count":a.vulnerable_count,
    "summary_of_issues":a.summary_of_issues,"summary_of_responses":a.summary_of_responses,
    "action_items":a.action_items,
    "minutes_url":a.minutes_url,"photos_urls":a.photos_urls,
    "languages_used":a.languages_used,
    "conducted_by_user_id":str(a.conducted_by_user_id) if a.conducted_by_user_id else None,
    "cancelled_reason":a.cancelled_reason,
    "created_at":a.created_at.isoformat(),"updated_at":a.updated_at.isoformat()
}
def _m_out(m): return {
    "id":str(m.id),"activity_id":str(m.activity_id),
    "media_type":m.media_type,"file_url":m.file_url,
    "file_name":m.file_name,"file_size_bytes":m.file_size_bytes,
    "mime_type":m.mime_type,"title":m.title,"description":m.description,
    "uploaded_by_user_id":str(m.uploaded_by_user_id) if m.uploaded_by_user_id else None,
    "uploaded_at":m.uploaded_at.isoformat()
}
def _e_out(e): return {"id":str(e.id),"contact_id":str(e.contact_id),"activity_id":str(e.activity_id),"attendance_status":e.attendance_status,"proxy_name":e.proxy_name,"concerns_raised":e.concerns_raised,"response_given":e.response_given,"feedback_submitted":e.feedback_submitted,"feedback_ref_id":str(e.feedback_ref_id) if e.feedback_ref_id else None,"notes":e.notes,"created_at":e.created_at.isoformat()}

@router.post("", status_code=status.HTTP_201_CREATED, summary="Create an engagement activity")
async def create_activity(body: Dict[str, Any], db: DbDep, kafka: KafkaDep, token: StaffDep) -> dict:
    return _a_out(await _svc(db, kafka).create(body, conducted_by=token.sub))

@router.get("", summary="List engagement activities")
async def list_activities(
    db: DbDep, kafka: KafkaDep, _: StaffDep,
    project_id: Optional[uuid.UUID] = Query(default=None),
    stage: Optional[str] = Query(default=None),
    status_: Optional[str] = Query(default=None, alias="status"),
    lga: Optional[str] = Query(default=None),
    skip: int = Query(default=0, ge=0), limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    items = await _svc(db, kafka).list(project_id=project_id, stage=stage, status=status_, lga=lga, skip=skip, limit=limit)
    return {"items": [_a_out(a) for a in items]}

@router.get("/{activity_id}", summary="Activity detail with attendance")
async def get_activity(activity_id: uuid.UUID, db: DbDep, kafka: KafkaDep, _: StaffDep) -> dict:
    a = await _svc(db, kafka).get_with_attendances_or_404(activity_id)
    return {**_a_out(a), "attendances": [_e_out(e) for e in a.attendances]}

@router.patch("/{activity_id}", summary="Update activity / mark as conducted")
async def update_activity(activity_id: uuid.UUID, body: Dict[str, Any], db: DbDep, kafka: KafkaDep, _: StaffDep) -> dict:
    return _a_out(await _svc(db, kafka).update(activity_id, body))

@router.post("/{activity_id}/attendances", status_code=status.HTTP_201_CREATED, summary="Log attendance")
async def log_attendance(activity_id: uuid.UUID, body: Dict[str, Any], db: DbDep, kafka: KafkaDep, token: StaffDep) -> dict:
    return _e_out(await _svc(db, kafka).log_attendance(activity_id, body, logged_by=token.sub))

@router.patch("/{activity_id}/attendances/{engagement_id}", summary="Update attendance record")
async def update_attendance(activity_id: uuid.UUID, engagement_id: uuid.UUID, body: Dict[str, Any], db: DbDep, kafka: KafkaDep, _: StaffDep) -> dict:
    return _e_out(await _svc(db, kafka).update_attendance(activity_id, engagement_id, body))


# ── Bulk attendance ────────────────────────────────────────────────────────────

@router.post("/{activity_id}/attendances/bulk", status_code=status.HTTP_201_CREATED,
             summary="Bulk log attendance — multiple contacts in one request")
async def bulk_log_attendance(
    activity_id: uuid.UUID,
    body: Dict[str, Any],   # {"records": [{contact_id, attendance_status?, concerns?, ...}]}
    db: DbDep, kafka: KafkaDep, token: StaffDep,
) -> dict:
    """
    Log attendance for multiple contacts at once.
    body = {"records": [{"contact_id": "...", "attendance_status": "attended", ...}, ...]}
    Useful for large meetings where attendees are known in advance.
    """
    records = body.get("records", [])
    if not records:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="records list is required and must not be empty.")
    results = await _svc(db, kafka).bulk_log_attendance(activity_id, records, logged_by=token.sub)
    return {"activity_id": str(activity_id), "logged": len(results), "items": [_e_out(e) for e in results]}


# ── Delete attendance ──────────────────────────────────────────────────────────

@router.delete("/{activity_id}/attendances/{engagement_id}",
               status_code=status.HTTP_200_OK,
               summary="Remove an attendance record")
async def delete_attendance(
    activity_id: uuid.UUID,
    engagement_id: uuid.UUID,
    db: DbDep, kafka: KafkaDep, _: StaffDep,
) -> dict:
    await _svc(db, kafka).delete_attendance(activity_id, engagement_id)
    return {"message": f"Attendance record {engagement_id} removed."}


# ── Cancel activity ────────────────────────────────────────────────────────────

@router.post("/{activity_id}/cancel", status_code=status.HTTP_200_OK,
             summary="Cancel a planned or scheduled activity")
async def cancel_activity(
    activity_id: uuid.UUID,
    body: Dict[str, Any],   # {"reason": "..."}
    db: DbDep, kafka: KafkaDep, _: StaffDep,
) -> dict:
    """Mark the activity as CANCELLED. Conducted activities cannot be cancelled."""
    from fastapi import HTTPException
    try:
        a = await _svc(db, kafka).cancel(activity_id, reason=body.get("reason"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _a_out(a)


# ── Media: upload ──────────────────────────────────────────────────────────────

@router.post("/{activity_id}/media", status_code=status.HTTP_201_CREATED,
             summary="Upload a file (photo, PDF minutes, presentation) to an activity")
async def upload_activity_media(
    activity_id:  uuid.UUID,
    file:         UploadFile = File(...),
    title:        str        = Form(...,       description="Short descriptive title (required)."),
    media_type:   str        = Form("document",description="minutes | photo | presentation | document | other"),
    description:  str        = Form("",        description="Detailed description of the file content."),
    db:           DbDep      = ...,
    kafka:        KafkaDep   = ...,
    token:        StaffDep   = ...,
) -> dict:
    """
    Upload a media file to an engagement activity.

    Accepted formats:
      · photos:        JPEG, PNG, WebP
      · minutes:       PDF
      · presentation:  PDF, PPTX
      · document:      PDF, DOCX, XLSX

    File is stored in MinIO at:
      activities/{activity_id}/media/{file_id}.{ext}

    The file is NEVER deleted — it is part of the SEP engagement evidence trail.
    """
    from core.config import settings as cfg
    from services.image_service import ImageUploadError
    from fastapi import HTTPException
    try:
        media = await _svc(db, kafka).upload_media(
            activity_id         = activity_id,
            file                = file,
            title               = title,
            media_type          = media_type,
            description         = description or None,
            uploaded_by_user_id = token.sub,
            settings            = cfg,
        )
    except (ImageUploadError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _m_out(media)


# ── Media: list ────────────────────────────────────────────────────────────────

@router.get("/{activity_id}/media", status_code=status.HTTP_200_OK,
            summary="List all media files attached to an activity")
async def list_activity_media(
    activity_id: uuid.UUID,
    media_type: Optional[str] = Query(default=None,
        description="Filter by type: minutes | photo | presentation | document | other"),
    db: DbDep = ..., kafka: KafkaDep = ..., _: StaffDep = ...,
) -> dict:
    media = await _svc(db, kafka).list_media(activity_id, media_type)
    return {
        "activity_id": str(activity_id),
        "total": len(media),
        "items": [_m_out(m) for m in media],
    }


# ── Media: delete ─────────────────────────────────────────────────────────────

@router.delete("/{activity_id}/media/{media_id}", status_code=status.HTTP_200_OK,
               summary="Remove a media file from an activity (soft delete)")
async def delete_activity_media(
    activity_id: uuid.UUID,
    media_id:    uuid.UUID,
    db: DbDep = ..., kafka: KafkaDep = ..., _: StaffDep = ...,
) -> dict:
    """
    Soft-deletes the media record. The file in MinIO/S3 is NEVER deleted —
    engagement media is part of the SEP evidence trail.
    """
    from fastapi import HTTPException
    try:
        await _svc(db, kafka).delete_media(activity_id, media_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Media file not found.")
    return {"message": f"Media {media_id} removed from activity."}

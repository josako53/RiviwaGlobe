# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  translation_service  |  Port: 8050
# FILE     :  api/v1/preferences.py
# ───────────────────────────────────────────────────────────────────────────
"""
api/v1/preferences.py — User language preference CRUD.

Translation service is a stateless engine called service-to-service.
All preference endpoints require X-Service-Key (not JWT).
Originating services (auth, notification, feedback) pass user_id in the path.

Routes (X-Service-Key required)
──────────────────────────────────────────────────────────
  GET    /preferences/{user_id}    Get preferences for a user
  PUT    /preferences/{user_id}    Create or replace (upsert)
  PATCH  /preferences/{user_id}    Partial update
  DELETE /preferences/{user_id}    Reset to platform defaults
  GET    /preferences/logs         Paginated detection log (admin read)
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import desc, select

from core.dependencies import DbDep, require_service_key
from models.language import LanguageDetectionLog, UserLanguagePreference

log    = structlog.get_logger(__name__)
router = APIRouter(
    tags=["Language Preferences"],
    dependencies=[Depends(require_service_key)],
)


# ── Schemas ───────────────────────────────────────────────────────────────────

class PreferenceUpsert(BaseModel):
    preferred_language:  str  = "sw"
    fallback_language:   str  = "en"
    device_locale:       Optional[str]  = None
    auto_detect_enabled: bool = True


class PreferencePatch(BaseModel):
    preferred_language:  Optional[str]  = None
    fallback_language:   Optional[str]  = None
    device_locale:       Optional[str]  = None
    auto_detect_enabled: Optional[bool] = None


def _pref_out(p: UserLanguagePreference) -> dict:
    return {
        "user_id":             str(p.user_id),
        "preferred_language":  p.preferred_language,
        "fallback_language":   p.fallback_language,
        "device_locale":       p.device_locale,
        "detected_languages":  p.detected_languages or {},
        "auto_detect_enabled": p.auto_detect_enabled,
        "created_at":          p.created_at.isoformat(),
        "updated_at":          p.updated_at.isoformat(),
    }


async def _get_pref(db, user_id: uuid.UUID) -> Optional[UserLanguagePreference]:
    return (
        await db.execute(
            select(UserLanguagePreference).where(UserLanguagePreference.user_id == user_id)
        )
    ).scalar_one_or_none()


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/preferences/{user_id}", summary="Get language preferences for a user")
async def get_preferences(user_id: uuid.UUID, db: DbDep) -> dict:
    pref = await _get_pref(db, user_id)
    if not pref:
        raise HTTPException(status_code=404, detail="No language preferences found for this user.")
    return _pref_out(pref)


@router.put(
    "/preferences/{user_id}",
    summary="Create or replace language preferences for a user",
    status_code=status.HTTP_200_OK,
)
async def upsert_preferences(user_id: uuid.UUID, body: PreferenceUpsert, db: DbDep) -> dict:
    pref = await _get_pref(db, user_id)
    if pref:
        pref.preferred_language  = body.preferred_language
        pref.fallback_language   = body.fallback_language
        pref.device_locale       = body.device_locale
        pref.auto_detect_enabled = body.auto_detect_enabled
        pref.updated_at          = datetime.utcnow()
    else:
        pref = UserLanguagePreference(
            user_id=user_id,
            preferred_language=body.preferred_language,
            fallback_language=body.fallback_language,
            device_locale=body.device_locale,
            auto_detect_enabled=body.auto_detect_enabled,
        )
        db.add(pref)
    await db.commit()
    await db.refresh(pref)
    return _pref_out(pref)


@router.patch("/preferences/{user_id}", summary="Partially update language preferences for a user")
async def patch_preferences(user_id: uuid.UUID, body: PreferencePatch, db: DbDep) -> dict:
    pref = await _get_pref(db, user_id)
    if not pref:
        raise HTTPException(
            status_code=404,
            detail="No preferences found. Use PUT /preferences/{user_id} to create them first.",
        )
    updates = body.model_dump(exclude_none=True)
    for field, value in updates.items():
        setattr(pref, field, value)
    pref.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(pref)
    return _pref_out(pref)


@router.delete(
    "/preferences/{user_id}",
    summary="Delete language preferences for a user (reset to defaults)",
)
async def delete_preferences(user_id: uuid.UUID, db: DbDep) -> dict:
    pref = await _get_pref(db, user_id)
    if not pref:
        return {"message": "No preferences to delete.", "user_id": str(user_id)}
    await db.delete(pref)
    await db.commit()
    return {"message": "Language preferences deleted.", "user_id": str(user_id)}


@router.get("/preferences/logs", summary="Paginated language detection log (admin read-only)")
async def list_detection_logs(
    db: DbDep,
    user_id:  Optional[uuid.UUID] = Query(default=None),
    channel:  Optional[str]       = Query(default=None),
    language: Optional[str]       = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=50, ge=1, le=200),
) -> dict:
    q = select(LanguageDetectionLog)
    if user_id:
        q = q.where(LanguageDetectionLog.user_id == user_id)
    if channel:
        q = q.where(LanguageDetectionLog.channel == channel)
    if language:
        q = q.where(LanguageDetectionLog.detected_language == language)
    q = q.order_by(desc(LanguageDetectionLog.created_at)).offset((page - 1) * size).limit(size)
    logs = (await db.execute(q)).scalars().all()
    return {
        "logs": [
            {
                "id":                 str(l.id),
                "user_id":            str(l.user_id) if l.user_id else None,
                "session_id":         l.session_id,
                "channel":            l.channel.value,
                "detection_source":   l.detection_source.value,
                "detected_language":  l.detected_language,
                "confidence":         l.confidence,
                "text_sample":        l.text_sample,
                "preference_updated": l.preference_updated,
                "created_at":         l.created_at.isoformat(),
            }
            for l in logs
        ],
        "page":  page,
        "count": len(logs),
    }

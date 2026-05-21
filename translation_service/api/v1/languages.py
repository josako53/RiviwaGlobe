# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  translation_service  |  Port: 8050
# FILE     :  api/v1/languages.py
# ───────────────────────────────────────────────────────────────────────────
"""
api/v1/languages.py — Admin CRUD for the supported_languages table.

Routes (all require platform admin JWT)
────────────────────────────────────────
  GET    /admin/languages           List all languages (incl. inactive)
  POST   /admin/languages           Add a new supported language
  GET    /admin/languages/{code}    Get a single language record
  PATCH  /admin/languages/{code}    Update language metadata or flags
  DELETE /admin/languages/{code}    Deactivate a language (soft-delete)
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select

from core.dependencies import DbDep, require_service_key
from models.language import SupportedLanguage

log    = structlog.get_logger(__name__)
router = APIRouter(
    prefix="/admin/languages",
    tags=["Languages — Admin"],
    dependencies=[Depends(require_service_key)],
)


# ── Schemas ───────────────────────────────────────────────────────────────────

class LanguageCreate(BaseModel):
    code:        str
    name:        str
    native_name: str
    flag_emoji:  Optional[str] = None
    is_rtl:      bool = False
    is_active:   bool = True
    google_supported: bool = True
    deepl_supported:  bool = False


class LanguageUpdate(BaseModel):
    name:        Optional[str]  = None
    native_name: Optional[str]  = None
    flag_emoji:  Optional[str]  = None
    is_rtl:      Optional[bool] = None
    is_active:   Optional[bool] = None
    google_supported: Optional[bool] = None
    deepl_supported:  Optional[bool] = None


def _out(lang: SupportedLanguage) -> dict:
    return {
        "code":             lang.code,
        "name":             lang.name,
        "native_name":      lang.native_name,
        "flag_emoji":       lang.flag_emoji,
        "is_rtl":           lang.is_rtl,
        "is_active":        lang.is_active,
        "google_supported": lang.google_supported,
        "deepl_supported":  lang.deepl_supported,
        "created_at":       lang.created_at.isoformat(),
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("", summary="List all supported languages (admin)")
async def list_languages(
    db: DbDep,
    active_only: bool = Query(default=False),
) -> dict:
    q = select(SupportedLanguage)
    if active_only:
        q = q.where(SupportedLanguage.is_active == True)
    langs = (await db.execute(q.order_by(SupportedLanguage.code))).scalars().all()
    return {"languages": [_out(l) for l in langs], "total": len(langs)}


@router.post("", summary="Add a new supported language", status_code=status.HTTP_201_CREATED)
async def create_language(body: LanguageCreate, db: DbDep) -> dict:
    existing = await db.get(SupportedLanguage, body.code.lower())
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Language code '{body.code}' already exists.",
        )
    lang = SupportedLanguage(
        code=body.code.lower(),
        name=body.name,
        native_name=body.native_name,
        flag_emoji=body.flag_emoji,
        is_rtl=body.is_rtl,
        is_active=body.is_active,
        google_supported=body.google_supported,
        deepl_supported=body.deepl_supported,
    )
    db.add(lang)
    await db.commit()
    await db.refresh(lang)
    log.info("language.created", code=lang.code)
    return _out(lang)


@router.get("/{code}", summary="Get a single language record (admin)")
async def get_language(code: str, db: DbDep) -> dict:
    lang = await db.get(SupportedLanguage, code.lower())
    if not lang:
        raise HTTPException(status_code=404, detail=f"Language '{code}' not found.")
    return _out(lang)


@router.patch("/{code}", summary="Update language metadata or provider flags")
async def update_language(code: str, body: LanguageUpdate, db: DbDep) -> dict:
    lang = await db.get(SupportedLanguage, code.lower())
    if not lang:
        raise HTTPException(status_code=404, detail=f"Language '{code}' not found.")

    updates = body.model_dump(exclude_none=True)
    for field, value in updates.items():
        setattr(lang, field, value)

    await db.commit()
    await db.refresh(lang)
    log.info("language.updated", code=lang.code, fields=list(updates.keys()))
    return _out(lang)


@router.delete("/{code}", summary="Deactivate a language (soft-delete)")
async def deactivate_language(code: str, db: DbDep) -> dict:
    lang = await db.get(SupportedLanguage, code.lower())
    if not lang:
        raise HTTPException(status_code=404, detail=f"Language '{code}' not found.")
    if not lang.is_active:
        return {"message": f"Language '{code}' is already inactive.", "code": lang.code}

    lang.is_active = False
    await db.commit()
    log.info("language.deactivated", code=lang.code)
    return {"message": f"Language '{code}' deactivated.", "code": lang.code}

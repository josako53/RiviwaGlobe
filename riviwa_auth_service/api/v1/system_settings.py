# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  riviwa_auth_service  |  Port: 8000  |  DB: auth_db (5433)
# FILE     :  api/v1/system_settings.py
# ───────────────────────────────────────────────────────────────────────────
"""
api/v1/system_settings.py
════════════════════════════════════════════════════════════════════════════
Platform-level system / app configuration endpoints.

Routes
──────
  Logo
    GET    /api/v1/system/logo          Public — get current platform logo URL
    POST   /api/v1/system/logo          super_admin — upload / replace platform logo
    DELETE /api/v1/system/logo          super_admin — remove platform logo

  Favicon
    GET    /api/v1/system/favicon       Public — get current favicon URL
    POST   /api/v1/system/favicon       super_admin — upload / replace favicon
    DELETE /api/v1/system/favicon       super_admin — remove favicon

  Settings (read / write)
    GET    /api/v1/system/settings      admin+ — read all platform settings
    PATCH  /api/v1/system/settings      super_admin — update name / colours / contact

Access model
────────────
  Public GETs (logo, favicon):   no auth required — the React app loads these
                                  on boot to render the correct branding.
  Admin GETs  (settings):        requires platform_role ≥ admin
  Writes      (POST, PATCH, DEL): requires platform_role = super_admin

MinIO storage paths
───────────────────
  system/platform/logo.{ext}
  system/platform/favicon.{ext}

Both paths sit under the "riviwa-images" bucket (same as org logos).

Kafka
─────
No Kafka events are published here — the platform logo is read by the
React client directly from this REST endpoint on boot, not from a cache.
════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from core.dependencies import DbDep, require_active_user, require_platform_role
from models.user import User

router = APIRouter(prefix="/system", tags=["Platform Settings"])

# ── Dependency aliases ─────────────────────────────────────────────────────────
_admin_guard      = Depends(require_platform_role("admin"))
_superadmin_guard = Depends(require_platform_role("super_admin"))

# Fixed PK — system_settings is a single-row table
_SETTINGS_ID = 1


# ── Schemas ────────────────────────────────────────────────────────────────────

class SystemSettingsRead(BaseModel):
    app_name:        str
    logo_url:        Optional[str]
    logo_updated_at: Optional[datetime]
    favicon_url:     Optional[str]
    support_email:   Optional[str]
    support_phone:   Optional[str]
    primary_color:   str
    secondary_color: str
    updated_at:      datetime

    model_config = {"from_attributes": True}


class SystemSettingsPatch(BaseModel):
    app_name:        Optional[str]  = Field(default=None, max_length=128)
    support_email:   Optional[str]  = Field(default=None, max_length=255)
    support_phone:   Optional[str]  = Field(default=None, max_length=30)
    primary_color:   Optional[str]  = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    secondary_color: Optional[str]  = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")


# ── Internal helper ────────────────────────────────────────────────────────────

async def _get_settings_row(db):
    """Fetch (and assert exists) the single system_settings row."""
    from sqlalchemy import select
    from models.system_settings import SystemSettings
    row = await db.scalar(select(SystemSettings).where(SystemSettings.id == _SETTINGS_ID))
    if not row:
        raise HTTPException(status_code=500, detail="System settings not initialised.")
    return row


# ══════════════════════════════════════════════════════════════════════════════
# LOGO — GET / POST / DELETE
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/logo",
    status_code=status.HTTP_200_OK,
    summary="Get platform logo",
    description=(
        "Returns the current platform logo URL. "
        "Public — no authentication required. "
        "The React app calls this on boot to render the correct branding. "
        "`logo_url` is null until a super_admin uploads a logo."
    ),
    responses={
        200: {"description": "Logo URL (may be null)"},
    },
)
async def get_platform_logo(db: DbDep) -> dict:
    row = await _get_settings_row(db)
    return {
        "logo_url":        row.logo_url,
        "logo_updated_at": row.logo_updated_at.isoformat() if row.logo_updated_at else None,
        "app_name":        row.app_name,
    }


@router.post(
    "/logo",
    status_code=status.HTTP_200_OK,
    summary="Upload / replace platform logo",
    description=(
        "Upload the system-wide app logo. "
        "Accepted formats: JPEG, PNG, WebP, SVG. Max 5 MB. "
        "Re-uploading overwrites the previous file in MinIO. "
        "Requires `super_admin` platform role."
    ),
    responses={
        200: {"description": "Logo uploaded — returns new logo_url"},
        400: {"description": "Invalid file type or file too large"},
        403: {"description": "super_admin role required"},
    },
)
async def upload_platform_logo(
    db:         DbDep,
    file:       UploadFile = File(..., description="Logo image (JPEG/PNG/WebP/SVG, max 5 MB)"),
    admin_user: User = _superadmin_guard,
) -> dict:
    """
    Upload or replace the platform logo.

    Flow:
      1. ImageService validates MIME type and size.
      2. File is stored in MinIO at system/platform/logo.{ext}.
         Re-uploading simply overwrites the previous object — no old files accumulate.
      3. system_settings.logo_url, logo_updated_at, logo_updated_by are updated.
    """
    from core.config import settings as cfg
    from services.image_service import ImageService, ImageUploadError
    from sqlalchemy import update
    from models.system_settings import SystemSettings

    img_svc = ImageService(cfg)
    try:
        logo_url = await img_svc.upload(
            file=file,
            entity_type="system",
            entity_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),  # fixed slot
            slot="logo",
        )
    except ImageUploadError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    now = datetime.now(timezone.utc)
    await db.execute(
        update(SystemSettings)
        .where(SystemSettings.id == _SETTINGS_ID)
        .values(
            logo_url=logo_url,
            logo_updated_at=now,
            logo_updated_by=admin_user.id,
            updated_at=now,
        )
    )
    await db.commit()

    return {
        "logo_url":        logo_url,
        "logo_updated_at": now.isoformat(),
        "uploaded_by":     str(admin_user.id),
    }


@router.delete(
    "/logo",
    status_code=status.HTTP_200_OK,
    summary="Remove platform logo",
    description=(
        "Delete the platform logo from MinIO and clear `logo_url`. "
        "The app will fall back to its default bundled logo. "
        "Requires `super_admin` platform role."
    ),
    responses={
        200: {"description": "Logo removed"},
        403: {"description": "super_admin role required"},
        404: {"description": "No logo is currently set"},
    },
)
async def delete_platform_logo(
    db:         DbDep,
    admin_user: User = _superadmin_guard,
) -> dict:
    from core.config import settings as cfg
    from services.image_service import ImageService
    from sqlalchemy import update
    from models.system_settings import SystemSettings

    row = await _get_settings_row(db)
    if not row.logo_url:
        raise HTTPException(status_code=404, detail="No platform logo is currently set.")

    # Delete from MinIO — tries all extensions, ignores missing
    img_svc = ImageService(cfg)
    await img_svc.delete(
        entity_type="system",
        entity_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        slot="logo",
    )

    now = datetime.now(timezone.utc)
    await db.execute(
        update(SystemSettings)
        .where(SystemSettings.id == _SETTINGS_ID)
        .values(logo_url=None, logo_updated_at=now, logo_updated_by=admin_user.id, updated_at=now)
    )
    await db.commit()

    return {"logo_url": None, "message": "Platform logo removed."}


# ══════════════════════════════════════════════════════════════════════════════
# FAVICON — GET / POST / DELETE
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/favicon",
    status_code=status.HTTP_200_OK,
    summary="Get platform favicon",
    description="Returns the current favicon URL. Public — no auth required.",
)
async def get_platform_favicon(db: DbDep) -> dict:
    row = await _get_settings_row(db)
    return {"favicon_url": row.favicon_url}


@router.post(
    "/favicon",
    status_code=status.HTTP_200_OK,
    summary="Upload / replace platform favicon",
    description=(
        "Upload the platform favicon (16×16 or 32×32, ICO/PNG/SVG, max 512 KB). "
        "Requires `super_admin` platform role."
    ),
    responses={
        200: {"description": "Favicon uploaded"},
        400: {"description": "Invalid file type or size exceeded"},
        403: {"description": "super_admin role required"},
    },
)
async def upload_platform_favicon(
    db:         DbDep,
    file:       UploadFile = File(..., description="Favicon (PNG/SVG/ICO, max 512 KB)"),
    admin_user: User = _superadmin_guard,
) -> dict:
    from core.config import settings as cfg
    from services.image_service import ImageService, ImageUploadError
    from sqlalchemy import update
    from models.system_settings import SystemSettings

    # Favicon gets a tighter size limit: 512 KB
    img_svc = ImageService(cfg)
    img_svc.max_bytes = 512 * 1024

    try:
        favicon_url = await img_svc.upload(
            file=file,
            entity_type="system",
            entity_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            slot="favicon",
        )
    except ImageUploadError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    now = datetime.now(timezone.utc)
    await db.execute(
        update(SystemSettings)
        .where(SystemSettings.id == _SETTINGS_ID)
        .values(favicon_url=favicon_url, updated_at=now)
    )
    await db.commit()
    return {"favicon_url": favicon_url}


@router.delete(
    "/favicon",
    status_code=status.HTTP_200_OK,
    summary="Remove platform favicon",
    description="Delete the platform favicon. Requires `super_admin` role.",
)
async def delete_platform_favicon(
    db:         DbDep,
    admin_user: User = _superadmin_guard,
) -> dict:
    from core.config import settings as cfg
    from services.image_service import ImageService
    from sqlalchemy import update
    from models.system_settings import SystemSettings

    row = await _get_settings_row(db)
    if not row.favicon_url:
        raise HTTPException(status_code=404, detail="No favicon is currently set.")

    img_svc = ImageService(cfg)
    await img_svc.delete(
        entity_type="system",
        entity_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        slot="favicon",
    )

    await db.execute(
        update(SystemSettings)
        .where(SystemSettings.id == _SETTINGS_ID)
        .values(favicon_url=None, updated_at=datetime.now(timezone.utc))
    )
    await db.commit()
    return {"favicon_url": None, "message": "Platform favicon removed."}


# ══════════════════════════════════════════════════════════════════════════════
# SETTINGS — GET / PATCH
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/settings",
    status_code=status.HTTP_200_OK,
    summary="Get all platform settings",
    description=(
        "Return the full system_settings row — app name, logo, favicon, "
        "contact details, brand colours. Requires `admin` platform role."
    ),
    response_model=SystemSettingsRead,
)
async def get_platform_settings(
    db:    DbDep,
    _auth: User = _admin_guard,
) -> SystemSettingsRead:
    row = await _get_settings_row(db)
    return SystemSettingsRead.model_validate(row)


@router.patch(
    "/settings",
    status_code=status.HTTP_200_OK,
    summary="Update platform settings",
    description=(
        "Update app name, support email/phone, or brand colours. "
        "All fields are optional — only provided fields are changed. "
        "Use the dedicated logo/favicon endpoints to change images. "
        "Requires `super_admin` platform role."
    ),
    response_model=SystemSettingsRead,
)
async def update_platform_settings(
    body:       SystemSettingsPatch,
    db:         DbDep,
    admin_user: User = _superadmin_guard,
) -> SystemSettingsRead:
    from sqlalchemy import update
    from models.system_settings import SystemSettings

    changes = body.model_dump(exclude_none=True)
    if not changes:
        raise HTTPException(status_code=400, detail="No fields provided to update.")

    changes["updated_at"] = datetime.now(timezone.utc)
    await db.execute(
        update(SystemSettings).where(SystemSettings.id == _SETTINGS_ID).values(**changes)
    )
    await db.commit()

    row = await _get_settings_row(db)
    return SystemSettingsRead.model_validate(row)

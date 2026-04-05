# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  riviwa_auth_service  |  Port: 8000  |  DB: auth_db (5433)
# FILE     :  services/project_image_service.py
# ───────────────────────────────────────────────────────────────────────────
"""
services/project_image_service.py
────────────────────────────────────────────────────────────────────────────
Business logic for project and sub-project progress image galleries.

Upload flow
───────────
1. Caller passes an UploadFile + metadata (title, description, phase,
   captured_at, location, GPS).
2. ImageService validates MIME type and size.
3. File is stored in MinIO at:
     projects/{project_id}/gallery/{image_id}.{ext}
     subprojects/{subproject_id}/gallery/{image_id}.{ext}
4. A ProjectProgressImage row is created with the permanent URL.

Gallery retrieval
─────────────────
Images are returned ordered by phase → display_order → captured_at so
a "before → during → after" narrative is natural.

Filtering by phase gives the PIU a concise view:
  GET .../images?phase=before   →  baseline condition photos
  GET .../images?phase=after    →  completion evidence photos
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from models.org_project import ProjectProgressImage, ImagePhase
from repositories.project_image_repository import ProjectImageRepository
from services.image_service import ImageService, ImageUploadError


class ProjectImageService:

    def __init__(self, db: AsyncSession, settings) -> None:
        self.db       = db
        self.repo     = ProjectImageRepository(db)
        self.img_svc  = ImageService(settings)

    # ── Internal helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _storage_entity_type(entity_type: str) -> str:
        """Map 'project'/'subproject' to MinIO path prefix."""
        return "projects" if entity_type == "project" else "subprojects"

    @staticmethod
    def _serialise(img: ProjectProgressImage) -> dict:
        return {
            "id":                   str(img.id),
            "entity_type":          img.entity_type,
            "entity_id":            str(img.entity_id),
            "image_url":            img.image_url,
            "thumbnail_url":        img.thumbnail_url,
            "phase":                img.phase,
            "title":                img.title,
            "description":          img.description,
            "display_order":        img.display_order,
            "location_description": img.location_description,
            "gps_lat":              img.gps_lat,
            "gps_lng":              img.gps_lng,
            "captured_at":          img.captured_at.isoformat() if img.captured_at else None,
            "uploaded_at":          img.uploaded_at.isoformat(),
            "uploaded_by_user_id":  str(img.uploaded_by_user_id) if img.uploaded_by_user_id else None,
        }

    # ── Upload ────────────────────────────────────────────────────────────────

    async def upload_image(
        self,
        entity_type:          str,            # "project" | "subproject"
        entity_id:            uuid.UUID,
        file,                                 # FastAPI UploadFile
        title:                str,
        phase:                str = ImagePhase.DURING,
        description:          Optional[str] = None,
        display_order:        int = 0,
        location_description: Optional[str] = None,
        gps_lat:              Optional[float] = None,
        gps_lng:              Optional[float] = None,
        captured_at:          Optional[datetime] = None,
        uploaded_by_user_id:  Optional[uuid.UUID] = None,
    ) -> dict:
        """
        Validate, store, and register a single progress image.

        Raises ImageUploadError on MIME or size violation.
        Raises ValueError on unknown entity_type or phase.
        """
        if entity_type not in ("project", "subproject"):
            raise ValueError(f"entity_type must be 'project' or 'subproject', got '{entity_type}'.")
        if phase not in {e.value for e in ImagePhase}:
            raise ValueError(
                f"phase must be one of {[e.value for e in ImagePhase]}, got '{phase}'."
            )

        # Generate the image id now so we can use it in the storage path
        image_id = uuid.uuid4()
        storage_type = self._storage_entity_type(entity_type)

        # Upload to object storage
        # Key: projects/{entity_id}/gallery/{image_id}.{ext}
        image_url = await self.img_svc.upload(
            file=file,
            entity_type=f"{storage_type}/{entity_id}/gallery",
            entity_id=image_id,
            slot="photo",
        )

        # Create DB record
        img = ProjectProgressImage(
            id=image_id,
            entity_type=entity_type,
            entity_id=entity_id,
            image_url=image_url,
            phase=phase,
            title=title.strip(),
            description=description,
            display_order=display_order,
            location_description=location_description,
            gps_lat=gps_lat,
            gps_lng=gps_lng,
            captured_at=captured_at,
            uploaded_by_user_id=uploaded_by_user_id,
        )
        img = await self.repo.create(img)
        await self.db.commit()
        return self._serialise(img)

    # ── List ──────────────────────────────────────────────────────────────────

    async def list_images(
        self,
        entity_type: str,
        entity_id:   uuid.UUID,
        phase:       Optional[str] = None,
        skip:        int = 0,
        limit:       int = 50,
    ) -> dict:
        """
        Return paginated gallery for a project or sub-project.

        Also returns phase_counts so the client can show
        "Before (3) | During (12) | After (5)" tab headers.
        """
        images       = await self.repo.list(entity_type, entity_id, phase, skip, limit)
        total        = await self.repo.count(entity_type, entity_id, phase)
        phase_counts = await self.repo.phase_counts(entity_type, entity_id)

        return {
            "entity_type":   entity_type,
            "entity_id":     str(entity_id),
            "phase_filter":  phase,
            "total":         total,
            "returned":      len(images),
            "phase_counts":  phase_counts,
            "items":         [self._serialise(img) for img in images],
        }

    # ── Get single ────────────────────────────────────────────────────────────

    async def get_image(
        self,
        image_id:    uuid.UUID,
        entity_type: str,
        entity_id:   uuid.UUID,
    ) -> dict:
        img = await self.repo.get_by_id(image_id, entity_type, entity_id)
        if not img:
            raise ValueError(f"Image {image_id} not found.")
        return self._serialise(img)

    # ── Update metadata ───────────────────────────────────────────────────────

    async def update_image(
        self,
        image_id:    uuid.UUID,
        entity_type: str,
        entity_id:   uuid.UUID,
        data:        dict,
    ) -> dict:
        """
        Update title, description, phase, display_order, location, GPS,
        or captured_at for an existing progress image.

        Coercions applied before passing to the repository:
          · captured_at str  → datetime (ISO 8601 string from schema field)
          · phase            → validated against ImagePhase enum values
        """
        img = await self.repo.get_by_id(image_id, entity_type, entity_id)
        if not img:
            raise ValueError(f"Image {image_id} not found.")

        # Make a safe copy so we don't mutate the caller's dict
        clean: dict = {}
        for k, v in data.items():
            if k == "captured_at" and isinstance(v, str):
                # Schema passes captured_at as ISO 8601 string — coerce to datetime
                try:
                    from datetime import datetime
                    clean[k] = datetime.fromisoformat(v)
                except ValueError:
                    raise ValueError(
                        f"captured_at must be a valid ISO 8601 datetime string, got: {v!r}"
                    )
            elif k == "phase" and v is not None:
                # Validate phase against ImagePhase enum
                valid_phases = {e.value for e in ImagePhase}
                if v not in valid_phases:
                    raise ValueError(
                        f"phase must be one of {sorted(valid_phases)}, got: {v!r}"
                    )
                clean[k] = v
            elif v is not None:
                clean[k] = v

        img = await self.repo.update(img, clean)
        await self.db.commit()
        return self._serialise(img)

    # ── Soft delete ───────────────────────────────────────────────────────────

    async def delete_image(
        self,
        image_id:    uuid.UUID,
        entity_type: str,
        entity_id:   uuid.UUID,
    ) -> None:
        """
        Soft-delete the image record. The file in object storage is NEVER
        deleted — it forms part of the project evidence trail.
        """
        img = await self.repo.get_by_id(image_id, entity_type, entity_id)
        if not img:
            raise ValueError(f"Image {image_id} not found.")
        await self.repo.soft_delete(img)
        await self.db.commit()

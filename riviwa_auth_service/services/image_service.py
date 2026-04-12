# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  riviwa_auth_service  |  Port: 8000  |  DB: auth_db (5433)
# FILE     :  services/image_service.py
# ───────────────────────────────────────────────────────────────────────────
"""
services/image_service.py
────────────────────────────────────────────────────────────────────────────
Thin wrapper around MinIO (S3-compatible) for image uploads.

Used by:
  · Organisation logo   → organisations/{org_id}/logo.{ext}
  · Project cover image → projects/{project_id}/cover.{ext}
  · Progress photos     → projects/{project_id}/gallery/{image_id}.{ext}

Storage path convention
───────────────────────
  {entity_type}/{entity_id}/{slot}.{ext}

  entity_type : organisations | projects | subprojects | …
  entity_id   : UUID of the owning record
  slot        : logo | cover | photo  (prevents collisions within the same entity)
  ext         : inferred from MIME type (jpg, png, webp, svg)

URL returned
────────────
  http(s)://{MINIO_ENDPOINT}/{IMAGES_BUCKET}/{entity_type}/{entity_id}/{slot}.{ext}

  This is the permanent public URL.  Store it in the DB column (e.g.
  Organisation.logo_url).  No pre-signing needed for public images.
"""
from __future__ import annotations

import uuid
from typing import Optional

ALLOWED_MIME_TYPES: dict[str, str] = {
    "image/jpeg":    "jpg",
    "image/png":     "png",
    "image/webp":    "webp",
    "image/svg+xml": "svg",
    "image/gif":     "gif",
}


class ImageUploadError(Exception):
    """Raised when MIME type or size validation fails."""


class ImageService:
    """
    Validates and stores a single image file in MinIO.

    Parameters
    ----------
    settings : Settings
        Pydantic-settings object.  Must expose:
          MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY,
          IMAGES_BUCKET, LOGO_MAX_BYTES.
    """

    def __init__(self, settings) -> None:
        self.endpoint   = settings.MINIO_ENDPOINT.rstrip("/")
        self.access_key = settings.MINIO_ACCESS_KEY
        self.secret_key = settings.MINIO_SECRET_KEY
        self.bucket     = settings.IMAGES_BUCKET
        self.max_bytes  = getattr(settings, "LOGO_MAX_BYTES", 5 * 1024 * 1024)

    # ── Public API ────────────────────────────────────────────────────────────

    async def upload(
        self,
        file,                    # FastAPI UploadFile
        entity_type: str,        # e.g. "organisations"
        entity_id:   uuid.UUID,
        slot:        str,        # "logo" | "cover" | "photo"
    ) -> str:
        """
        Validate and upload *file* to MinIO.  Returns the permanent URL.

        Raises
        ------
        ImageUploadError
            · If MIME type is not in ALLOWED_MIME_TYPES.
            · If file size exceeds LOGO_MAX_BYTES.
        """
        # ── MIME validation ───────────────────────────────────────────────────
        content_type = (file.content_type or "").lower()
        ext = ALLOWED_MIME_TYPES.get(content_type)
        if not ext:
            raise ImageUploadError(
                f"Unsupported file type '{content_type}'. "
                f"Accepted: {', '.join(ALLOWED_MIME_TYPES)}."
            )

        # ── Read + size check ─────────────────────────────────────────────────
        data = await file.read()
        if len(data) > self.max_bytes:
            mb = self.max_bytes / (1024 * 1024)
            raise ImageUploadError(
                f"File too large ({len(data) / (1024*1024):.1f} MB). "
                f"Maximum allowed: {mb:.0f} MB."
            )

        # ── Build object key ──────────────────────────────────────────────────
        key = f"{entity_type}/{entity_id}/{slot}.{ext}"

        # ── Upload ────────────────────────────────────────────────────────────
        await self._put_object(key=key, data=data, content_type=content_type)

        return f"{self.endpoint}/{self.bucket}/{key}"

    async def delete(
        self,
        entity_type: str,
        entity_id:   uuid.UUID,
        slot:        str,
        ext:         Optional[str] = None,
    ) -> None:
        """
        Delete an object from MinIO.

        If *ext* is None, tries all supported extensions and silently ignores
        NoSuchKey errors — this covers the case where the actual extension is
        unknown at call time.
        """
        extensions = [ext] if ext else list(ALLOWED_MIME_TYPES.values())
        for e in extensions:
            key = f"{entity_type}/{entity_id}/{slot}.{e}"
            try:
                await self._delete_object(key)
            except Exception:
                pass  # object may not exist for this extension — that's fine

    # ── MinIO helpers ─────────────────────────────────────────────────────────

    async def _put_object(self, key: str, data: bytes, content_type: str) -> None:
        import aiobotocore.session  # type: ignore
        session = aiobotocore.session.get_session()
        async with session.create_client(
            "s3",
            endpoint_url=self.endpoint,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
        ) as client:
            await client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            )

    async def _delete_object(self, key: str) -> None:
        import aiobotocore.session  # type: ignore
        session = aiobotocore.session.get_session()
        async with session.create_client(
            "s3",
            endpoint_url=self.endpoint,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
        ) as client:
            await client.delete_object(Bucket=self.bucket, Key=key)

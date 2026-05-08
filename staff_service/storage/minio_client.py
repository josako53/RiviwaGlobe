"""storage/minio_client.py — MinIO client wrapper for staff_service."""
from __future__ import annotations

import io
from typing import List, Optional, Tuple
from uuid import UUID

import structlog
from minio import Minio
from minio.error import S3Error

from core.config import settings
from core.exceptions import FileTooLargeError, InvalidFileTypeError

log = structlog.get_logger(__name__)

_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
_MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

_client: Optional[Minio] = None


def get_minio_client() -> Minio:
    global _client
    if _client is None:
        endpoint = settings.MINIO_ENDPOINT
        # Strip protocol prefix if present
        for prefix in ("http://", "https://"):
            if endpoint.startswith(prefix):
                endpoint = endpoint[len(prefix):]
        _client = Minio(
            endpoint,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_USE_SSL,
        )
    return _client


async def ensure_bucket_exists() -> None:
    """Create the staff bucket if it does not exist. Called on startup."""
    client = get_minio_client()
    bucket = settings.STAFF_BUCKET
    try:
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
            log.info("staff_service.minio.bucket_created", bucket=bucket)
        else:
            log.info("staff_service.minio.bucket_exists", bucket=bucket)
    except Exception as exc:
        log.error("staff_service.minio.bucket_ensure_failed", bucket=bucket, error=str(exc))


def _validate_image(filename: str, content_type: str, size: int) -> None:
    import os
    ext = os.path.splitext(filename.lower())[1]
    if ext not in _ALLOWED_EXTENSIONS and content_type.lower() not in _ALLOWED_CONTENT_TYPES:
        raise InvalidFileTypeError()
    if size > _MAX_FILE_SIZE:
        raise FileTooLargeError()


def upload_staff_photo(
    org_id: UUID,
    staff_id: UUID,
    filename: str,
    data: bytes,
    content_type: str,
) -> Tuple[str, str]:
    """
    Upload a staff profile photo.
    Returns (object_key, presigned_url).
    """
    import datetime
    import os
    _validate_image(filename, content_type, len(data))
    ext = os.path.splitext(filename.lower())[1] or ".jpg"
    key = f"{org_id}/staff/{staff_id}/{filename}"
    client = get_minio_client()
    client.put_object(
        settings.STAFF_BUCKET,
        key,
        io.BytesIO(data),
        length=len(data),
        content_type=content_type,
    )
    url = client.presigned_get_object(
        settings.STAFF_BUCKET,
        key,
        expires=datetime.timedelta(days=7),
    )
    log.info("staff_service.minio.photo_uploaded", key=key)
    return key, url


def upload_fraud_photo(
    org_id: UUID,
    report_id: UUID,
    filename: str,
    data: bytes,
    content_type: str,
) -> Tuple[str, str]:
    """
    Upload a fraud report photo.
    Returns (object_key, presigned_url).
    """
    import datetime
    _validate_image(filename, content_type, len(data))
    key = f"{org_id}/fraud/{report_id}/{filename}"
    client = get_minio_client()
    client.put_object(
        settings.STAFF_BUCKET,
        key,
        io.BytesIO(data),
        length=len(data),
        content_type=content_type,
    )
    url = client.presigned_get_object(
        settings.STAFF_BUCKET,
        key,
        expires=datetime.timedelta(days=7),
    )
    log.info("staff_service.minio.fraud_photo_uploaded", key=key)
    return key, url


def upload_csv_file(
    org_id: UUID,
    job_id: UUID,
    filename: str,
    data: bytes,
) -> str:
    """Upload a bulk import CSV. Returns the object key."""
    key = f"{org_id}/imports/{job_id}/{filename}"
    client = get_minio_client()
    client.put_object(
        settings.STAFF_BUCKET,
        key,
        io.BytesIO(data),
        length=len(data),
        content_type="text/csv",
    )
    log.info("staff_service.minio.csv_uploaded", key=key)
    return key


def get_presigned_url(key: str, expires_days: int = 7) -> str:
    """Generate a fresh presigned URL for an existing object."""
    import datetime
    client = get_minio_client()
    return client.presigned_get_object(
        settings.STAFF_BUCKET,
        key,
        expires=datetime.timedelta(days=expires_days),
    )

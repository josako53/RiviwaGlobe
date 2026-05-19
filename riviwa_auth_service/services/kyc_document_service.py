"""services/kyc_document_service.py — MinIO upload for KYC documents."""
from __future__ import annotations

import uuid

ALLOWED_TYPES: dict[str, str] = {
    "application/pdf":                                                "pdf",
    "image/jpeg":                                                     "jpg",
    "image/png":                                                      "png",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/msword":                                             "doc",
    "image/tiff":                                                     "tiff",
}

MAX_BYTES = 15 * 1024 * 1024  # 15 MB


class KYCUploadError(Exception):
    pass


class KYCDocumentService:
    def __init__(self, settings) -> None:
        self.endpoint   = settings.MINIO_ENDPOINT.rstrip("/")
        self.access_key = settings.MINIO_ACCESS_KEY
        self.secret_key = settings.MINIO_SECRET_KEY
        self.bucket     = getattr(settings, "KYC_BUCKET", "riviwa-kyc")

    async def upload(
        self,
        file,
        org_id:        uuid.UUID,
        submission_id: uuid.UUID,
        document_type: str,
    ) -> tuple[str, str, int]:
        """
        Upload a KYC document file to MinIO.
        Returns (file_url, file_name, file_size_bytes).
        """
        content_type = (file.content_type or "application/octet-stream").lower()
        ext = ALLOWED_TYPES.get(content_type)
        if not ext:
            # Try to infer from filename
            fname = getattr(file, "filename", "") or ""
            for allowed_ext in ALLOWED_TYPES.values():
                if fname.lower().endswith(f".{allowed_ext}"):
                    ext = allowed_ext
                    break
        if not ext:
            raise KYCUploadError(
                f"Unsupported file type '{content_type}'. "
                f"Accepted: PDF, JPEG, PNG, DOCX, DOC, TIFF."
            )

        data = await file.read()
        if len(data) > MAX_BYTES:
            raise KYCUploadError(
                f"File too large ({len(data) / 1_048_576:.1f} MB). Maximum: 15 MB."
            )
        if len(data) == 0:
            raise KYCUploadError("File is empty.")

        short = uuid.uuid4().hex[:8]
        safe_type = document_type.replace(" ", "_").lower()
        original_name = getattr(file, "filename", None) or f"{safe_type}.{ext}"
        key = f"kyc/{org_id}/{submission_id}/{safe_type}_{short}.{ext}"

        await self._ensure_bucket()
        await self._put(key, data, content_type)

        url = f"{self.endpoint}/{self.bucket}/{key}"
        return url, original_name, len(data)

    async def delete(self, file_url: str) -> None:
        prefix = f"{self.endpoint}/{self.bucket}/"
        if not file_url.startswith(prefix):
            return
        key = file_url[len(prefix):]
        try:
            await self._delete(key)
        except Exception:
            pass

    async def _ensure_bucket(self) -> None:
        import aiobotocore.session
        session = aiobotocore.session.get_session()
        async with session.create_client(
            "s3",
            endpoint_url=self.endpoint,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
        ) as client:
            try:
                await client.head_bucket(Bucket=self.bucket)
            except Exception:
                try:
                    await client.create_bucket(Bucket=self.bucket)
                except Exception:
                    pass

    async def _put(self, key: str, data: bytes, content_type: str) -> None:
        import aiobotocore.session
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

    async def _delete(self, key: str) -> None:
        import aiobotocore.session
        session = aiobotocore.session.get_session()
        async with session.create_client(
            "s3",
            endpoint_url=self.endpoint,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
        ) as client:
            await client.delete_object(Bucket=self.bucket, Key=key)

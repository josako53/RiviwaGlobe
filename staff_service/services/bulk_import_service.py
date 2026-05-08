"""services/bulk_import_service.py — CSV bulk staff import logic."""
from __future__ import annotations

import asyncio
import datetime as dt
import io
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import structlog

from db.session import AsyncSessionLocal
from models.bulk_import import BulkImportJob
from repositories.bulk_import_repository import BulkImportRepository
from repositories.org_cache_repository import OrgCacheRepository
from repositories.staff_profile_repository import StaffProfileRepository
from models.staff_profile import StaffProfile

log = structlog.get_logger(__name__)

# Required columns (case-insensitive)
_REQUIRED_COLS = {"first_name", "last_name", "position"}

# Column mappings (normalised name → model field)
_COL_MAP = {
    "first_name": "first_name",
    "last_name": "last_name",
    "phone": "phone",
    "email": "email",
    "position": "position",
    "department": "department",
    "branch_name": "branch_name",
    "employment_type": "employment_type",
    "id_number": "id_number",
    "hire_date": "hire_date",
    "expertise": "expertise",
    "bio": "bio",
    "badge_number": "badge_number",
}

_VALID_EMPLOYMENT_TYPES = {"FULL_TIME", "PART_TIME", "CONTRACT", "INTERN", "VOLUNTEER"}


def _parse_row(row: Dict[str, Any], row_index: int) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Validate and parse a single CSV row. Returns (parsed_dict, error_message)."""
    parsed: Dict[str, Any] = {}

    for col, field in _COL_MAP.items():
        val = row.get(col, "").strip() if row.get(col) is not None else ""
        if col in _REQUIRED_COLS and not val:
            return None, f"Row {row_index}: missing required field '{col}'"
        parsed[field] = val or None

    # employment_type normalisation
    emp_type = (parsed.get("employment_type") or "FULL_TIME").upper()
    if emp_type not in _VALID_EMPLOYMENT_TYPES:
        emp_type = "FULL_TIME"
    parsed["employment_type"] = emp_type

    # expertise: semicolon-separated → list
    expertise_raw = parsed.get("expertise")
    if expertise_raw:
        parsed["expertise"] = [s.strip() for s in expertise_raw.split(";") if s.strip()]
    else:
        parsed["expertise"] = None

    # hire_date: try to parse YYYY-MM-DD
    hire_date_raw = parsed.get("hire_date")
    if hire_date_raw:
        try:
            parsed["hire_date"] = dt.date.fromisoformat(hire_date_raw)
        except (ValueError, TypeError):
            parsed["hire_date"] = None
    else:
        parsed["hire_date"] = None

    return parsed, None


async def _process_import(job_id: UUID, org_id: UUID, csv_bytes: bytes) -> None:
    """Run the import in the background using asyncio (not Celery)."""
    import pandas as pd

    successful = 0
    failed = 0
    errors: List[Dict[str, Any]] = []

    try:
        df = pd.read_csv(io.BytesIO(csv_bytes))
        # Normalise column names
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        # Fill NaN with empty string
        df = df.where(df.notna(), other="")
        rows = df.to_dict(orient="records")
        total = len(rows)
    except Exception as exc:
        async with AsyncSessionLocal() as db:
            repo = BulkImportRepository(db)
            job = await repo.get_by_id(job_id)
            if job:
                await repo.mark_failed(job, [{"row": 0, "error": f"CSV parse error: {exc}"}])
            await db.commit()
        log.error("staff.bulk_import.csv_parse_error", job_id=str(job_id), error=str(exc))
        return

    # Update total_rows
    async with AsyncSessionLocal() as db:
        repo = BulkImportRepository(db)
        job = await repo.get_by_id(job_id)
        if job:
            job.status = "PROCESSING"
            job.total_rows = total
            db.add(job)
            await db.commit()
        org_repo = OrgCacheRepository(db)
        org = await org_repo.get(org_id)
        org_slug = org.slug if org else None

    for i, row in enumerate(rows, start=2):
        parsed, err = _parse_row(row, i)
        if err:
            failed += 1
            errors.append({"row": i, "error": err})
            continue

        async with AsyncSessionLocal() as db:
            profile_repo = StaffProfileRepository(db)
            try:
                # Skip duplicates: badge_number or email already in org
                badge = parsed.get("badge_number")
                email = parsed.get("email")
                if badge:
                    existing = await profile_repo.get_by_badge_number(org_id, badge)
                    if existing:
                        failed += 1
                        errors.append({"row": i, "error": f"Duplicate badge_number: {badge}"})
                        continue
                if email:
                    existing = await profile_repo.get_by_email(org_id, email)
                    if existing:
                        failed += 1
                        errors.append({"row": i, "error": f"Duplicate email: {email}"})
                        continue

                seq = await profile_repo.next_sequence(org_id)
                # Format code
                prefix = (org_slug or "ORG").upper()[:6]
                staff_code = f"{prefix}-{seq:05d}"

                fn = parsed["first_name"] or ""
                ln = parsed["last_name"] or ""
                display_name = f"{fn} {ln}".strip()

                profile = StaffProfile(
                    org_id=org_id,
                    staff_code=staff_code,
                    display_name=display_name,
                    first_name=parsed["first_name"],
                    last_name=parsed["last_name"],
                    phone=parsed.get("phone"),
                    email=parsed.get("email"),
                    position=parsed["position"],
                    department=parsed.get("department"),
                    branch_name=parsed.get("branch_name"),
                    employment_type=parsed["employment_type"],
                    id_number=parsed.get("id_number"),
                    hire_date=parsed.get("hire_date"),
                    expertise=parsed.get("expertise"),
                    bio=parsed.get("bio"),
                    badge_number=parsed.get("badge_number"),
                    status="ACTIVE",
                )
                db.add(profile)
                await db.commit()
                successful += 1
            except Exception as exc:
                await db.rollback()
                failed += 1
                errors.append({"row": i, "error": str(exc)})
                log.error("staff.bulk_import.row_error", row=i, error=str(exc))

    async with AsyncSessionLocal() as db:
        repo = BulkImportRepository(db)
        job = await repo.get_by_id(job_id)
        if job:
            await repo.mark_completed(job, successful, failed, errors)
        await db.commit()

    log.info("staff.bulk_import.completed", job_id=str(job_id), successful=successful, failed=failed)


class BulkImportService:
    def __init__(self) -> None:
        pass

    async def start_import(
        self,
        org_id: UUID,
        imported_by: Optional[UUID],
        filename: str,
        file_key: str,
        csv_bytes: bytes,
    ) -> BulkImportJob:
        """Create job record, then launch background task."""
        async with AsyncSessionLocal() as db:
            repo = BulkImportRepository(db)
            job = BulkImportJob(
                org_id=org_id,
                imported_by=imported_by,
                file_key=file_key,
                original_filename=filename,
                status="PENDING",
            )
            job = await repo.create(job)
            await db.commit()
            await db.refresh(job)
            job_id = job.id

        # Launch background without blocking
        asyncio.create_task(_process_import(job_id, org_id, csv_bytes))
        return job

    async def get_job(self, job_id: UUID) -> BulkImportJob:
        from core.exceptions import BulkImportJobNotFoundError
        async with AsyncSessionLocal() as db:
            repo = BulkImportRepository(db)
            job = await repo.get_by_id(job_id)
            if not job:
                raise BulkImportJobNotFoundError()
            return job

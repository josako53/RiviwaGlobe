"""repositories/bulk_import_repository.py — BulkImportJob DB ops."""
from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.bulk_import import BulkImportJob


class BulkImportRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, job: BulkImportJob) -> BulkImportJob:
        self.db.add(job)
        await self.db.flush()
        return job

    async def get_by_id(self, job_id: UUID) -> Optional[BulkImportJob]:
        return await self.db.get(BulkImportJob, job_id)

    async def update(self, job: BulkImportJob, data: Dict[str, Any]) -> BulkImportJob:
        for k, v in data.items():
            setattr(job, k, v)
        self.db.add(job)
        await self.db.flush()
        return job

    async def mark_completed(
        self,
        job: BulkImportJob,
        successful_rows: int,
        failed_rows: int,
        errors: Optional[List[Any]] = None,
    ) -> BulkImportJob:
        job.status = "COMPLETED"
        job.successful_rows = successful_rows
        job.failed_rows = failed_rows
        job.errors = errors or []
        job.completed_at = dt.datetime.utcnow()
        self.db.add(job)
        await self.db.flush()
        return job

    async def mark_failed(self, job: BulkImportJob, errors: Optional[List[Any]] = None) -> BulkImportJob:
        job.status = "FAILED"
        job.errors = errors or []
        job.completed_at = dt.datetime.utcnow()
        self.db.add(job)
        await self.db.flush()
        return job

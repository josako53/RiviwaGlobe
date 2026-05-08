"""models/bulk_import.py — BulkImportJob."""
import datetime as dt
from typing import Any, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class BulkImportJob(SQLModel, table=True):
    __tablename__ = "bulk_import_jobs"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    org_id: UUID = Field(index=True)
    imported_by: Optional[UUID] = Field(default=None)

    file_key: str = Field(max_length=500)
    original_filename: str = Field(max_length=300)

    status: str = Field(default="PENDING", max_length=20)
    total_rows: int = Field(default=0)
    successful_rows: int = Field(default=0)
    failed_rows: int = Field(default=0)
    errors: Optional[List[Any]] = Field(default=None, sa_column=Column(JSONB, nullable=True))

    created_at: dt.datetime = Field(default_factory=dt.datetime.utcnow)
    completed_at: Optional[dt.datetime] = Field(default=None)

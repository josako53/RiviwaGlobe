"""models/staff_fraud_report.py — StaffFraudReport."""
import datetime as dt
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class StaffFraudReport(SQLModel, table=True):
    __tablename__ = "staff_fraud_reports"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    verification_event_id: Optional[UUID] = Field(
        default=None,
        foreign_key="staff_verifications.id",
        sa_column_kwargs={"onupdate": None},
    )
    org_id: Optional[UUID] = Field(default=None, index=True)

    reporter_name: Optional[str] = Field(default=None, max_length=200)
    reporter_phone: Optional[str] = Field(default=None, max_length=20)
    reporter_email: Optional[str] = Field(default=None, max_length=200)

    claimed_staff_name: Optional[str] = Field(default=None, max_length=200)
    claimed_staff_id: Optional[str] = Field(default=None, max_length=100)

    description: str = Field(sa_column=Column(Text, nullable=False))

    photo_keys: Optional[List[Any]] = Field(default=None, sa_column=Column(JSONB, nullable=True))
    photo_urls: Optional[List[Any]] = Field(default=None, sa_column=Column(JSONB, nullable=True))

    status: str = Field(default="SUBMITTED", max_length=20)
    ai_analysis: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSONB, nullable=True))

    assigned_agent_id: Optional[UUID] = Field(default=None)
    resolution_notes: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))

    created_at: dt.datetime = Field(default_factory=dt.datetime.utcnow, index=True)
    updated_at: dt.datetime = Field(default_factory=dt.datetime.utcnow)

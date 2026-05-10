"""models/staff_feedback.py — StaffFeedback."""
import datetime as dt
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, Text
from sqlmodel import Field, SQLModel

# Mirrors Riviwa core feedback vocabulary. Performance = applause_rate (applause / total).
FEEDBACK_TYPES = {"grievance", "suggestion", "applause", "inquiry"}


class StaffFeedback(SQLModel, table=True):
    __tablename__ = "staff_feedbacks"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    verification_event_id: UUID = Field(
        foreign_key="staff_verifications.id",
        index=True,
    )
    staff_id: UUID = Field(
        foreign_key="staff_profiles.id",
        index=True,
    )
    org_id: UUID = Field(index=True)

    feedback_type: str = Field(max_length=20, index=True)
    comment: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    service_type: Optional[str] = Field(default=None, max_length=200)
    location_description: Optional[str] = Field(default=None, max_length=500)
    location_lat: Optional[float] = Field(default=None)
    location_lng: Optional[float] = Field(default=None)

    is_anonymous: bool = Field(default=False)
    submitter_name: Optional[str] = Field(default=None, max_length=200)
    submitter_phone: Optional[str] = Field(default=None, max_length=20)

    created_at: dt.datetime = Field(default_factory=dt.datetime.utcnow, index=True)

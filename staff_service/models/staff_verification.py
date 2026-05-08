"""models/staff_verification.py — StaffVerificationEvent."""
import datetime as dt
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class StaffVerificationEvent(SQLModel, table=True):
    __tablename__ = "staff_verifications"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    lookup_code: str = Field(max_length=50, index=True)
    staff_id: Optional[UUID] = Field(
        default=None,
        foreign_key="staff_profiles.id",
        sa_column_kwargs={"onupdate": None},
    )
    org_id: Optional[UUID] = Field(default=None, index=True)
    result: str = Field(max_length=20, index=True)

    scanner_lat: Optional[float] = Field(default=None)
    scanner_lng: Optional[float] = Field(default=None)
    scanner_ip: Optional[str] = Field(default=None, max_length=45)
    user_agent: Optional[str] = Field(default=None, max_length=512)

    verified_at: dt.datetime = Field(default_factory=dt.datetime.utcnow, index=True)

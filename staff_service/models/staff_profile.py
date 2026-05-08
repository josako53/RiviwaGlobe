"""models/staff_profile.py — StaffProfile and StaffIdSequence."""
import datetime as dt
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, Index, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class StaffIdSequence(SQLModel, table=True):
    __tablename__ = "staff_id_sequences"
    __table_args__ = (UniqueConstraint("org_id", name="uq_staff_id_seq_org"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    org_id: UUID = Field(index=True)
    last_value: int = Field(default=0)


class StaffProfile(SQLModel, table=True):
    __tablename__ = "staff_profiles"
    __table_args__ = (
        UniqueConstraint("org_id", "staff_code", name="uq_sp_org_code"),
        Index("ix_sp_org_id", "org_id"),
        Index("ix_sp_status", "status"),
        Index("ix_sp_department", "department"),
        Index("ix_sp_branch_id", "branch_id"),
        Index("ix_sp_supervisor_id", "supervisor_id"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    org_id: UUID = Field()
    staff_code: str = Field(max_length=30)
    qr_code_id: Optional[UUID] = Field(default=None)
    badge_number: Optional[str] = Field(default=None, max_length=100)

    first_name: str = Field(max_length=100)
    last_name: str = Field(max_length=100)
    middle_name: Optional[str] = Field(default=None, max_length=100)
    display_name: str = Field(max_length=200)

    phone: Optional[str] = Field(default=None, max_length=20)
    email: Optional[str] = Field(default=None, max_length=200)

    position: str = Field(max_length=200)
    department: Optional[str] = Field(default=None, max_length=200)
    branch_id: Optional[UUID] = Field(default=None)
    branch_name: Optional[str] = Field(default=None, max_length=200)

    supervisor_id: Optional[UUID] = Field(
        default=None,
        foreign_key="staff_profiles.id",
        sa_column_kwargs={"onupdate": None},
    )

    employment_type: str = Field(max_length=20, default="FULL_TIME")
    status: str = Field(max_length=20, default="ACTIVE")

    expertise: Optional[List[Any]] = Field(default=None, sa_column=Column(JSONB, nullable=True))
    bio: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))

    photo_key: Optional[str] = Field(default=None, max_length=500)
    photo_url: Optional[str] = Field(default=None, max_length=500)

    id_number: Optional[str] = Field(default=None, max_length=100)
    project_ids: Optional[List[Any]] = Field(default=None, sa_column=Column(JSONB, nullable=True))
    metadata_: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column("metadata", JSONB, nullable=True),
    )

    is_verified: bool = Field(default=False)
    hire_date: Optional[dt.date] = Field(default=None)
    suspension_reason: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    termination_reason: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))

    created_by: Optional[UUID] = Field(default=None)
    created_at: dt.datetime = Field(default_factory=dt.datetime.utcnow)
    updated_at: dt.datetime = Field(default_factory=dt.datetime.utcnow)

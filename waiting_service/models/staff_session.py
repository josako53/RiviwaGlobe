
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

import sqlalchemy.dialects.postgresql as pg
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer
from sqlalchemy.sql import func
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from models.staff_counter import StaffCounter


class StaffSession(SQLModel, table=True):
    """Tracks a staff member's active work session at a specific counter."""
    __tablename__ = "staff_sessions"
    __table_args__ = (
        Index("ix_ss_org_id",            "org_id"),
        Index("ix_ss_staff_user_id",     "staff_user_id"),
        Index("ix_ss_staff_counter_id",  "staff_counter_id"),
        Index("ix_ss_service_point_id",  "service_point_id"),
        Index("ix_ss_is_active",         "is_active"),
    )

    id: uuid.UUID = Field(
        sa_column=Column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    )
    org_id: uuid.UUID = Field(sa_column=Column(pg.UUID(as_uuid=True), nullable=False, index=True))
    staff_user_id: Optional[uuid.UUID] = Field(
        default=None, sa_column=Column(pg.UUID(as_uuid=True), nullable=True, index=True)
    )
    staff_counter_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("staff_counters.id", ondelete="CASCADE"),
            nullable=False, index=True,
        )
    )
    service_point_id: uuid.UUID = Field(
        sa_column=Column(pg.UUID(as_uuid=True), nullable=False, index=True)
    )
    opened_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
    closed_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    is_active: bool = Field(default=True, sa_column=Column(Boolean, nullable=False, default=True, index=True))
    tickets_served: int = Field(default=0, sa_column=Column(Integer, nullable=False, default=0))
    avg_service_seconds: float = Field(default=0.0, sa_column=Column(Float, nullable=False, default=0.0))
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    )

    counter: "StaffCounter" = Relationship(back_populates="sessions")


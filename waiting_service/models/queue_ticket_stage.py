
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

import sqlalchemy.dialects.postgresql as pg
from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, Text
from sqlalchemy.sql import func
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from models.queue_ticket import QueueTicket
    from models.service_point import ServicePoint


class StageStatus:
    WAITING   = "WAITING"
    ATTENDING = "ATTENDING"
    FINISHED  = "FINISHED"
    SKIPPED   = "SKIPPED"


class QueueTicketStage(SQLModel, table=True):
    """One record per stage a ticket passes through, tracking dwell times."""
    __tablename__ = "queue_ticket_stages"
    __table_args__ = (
        Index("ix_qts_ticket_id",        "ticket_id"),
        Index("ix_qts_service_point_id", "service_point_id"),
        Index("ix_qts_staff_counter_id", "staff_counter_id"),
        Index("ix_qts_status",           "status"),
    )

    id: uuid.UUID = Field(
        sa_column=Column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    )
    ticket_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("queue_tickets.id", ondelete="CASCADE"),
            nullable=False, index=True,
        )
    )
    service_point_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("service_points.id", ondelete="RESTRICT"),
            nullable=False, index=True,
        )
    )
    step_order: int = Field(sa_column=Column(Integer, nullable=False))
    staff_counter_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("staff_counters.id", ondelete="SET NULL"),
            nullable=True, index=True,
        ),
    )
    assigned_staff_user_id: Optional[uuid.UUID] = Field(
        default=None, sa_column=Column(pg.UUID(as_uuid=True), nullable=True)
    )
    status: str = Field(
        default=StageStatus.WAITING,
        sa_column=Column(
            pg.ENUM("WAITING", "ATTENDING", "FINISHED", "SKIPPED", name="stage_status"),
            nullable=False, index=True,
        ),
    )
    entered_queue_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
    attending_started_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    finished_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    wait_duration_seconds: Optional[float] = Field(default=None, sa_column=Column(Float, nullable=True))
    service_duration_seconds: Optional[float] = Field(default=None, sa_column=Column(Float, nullable=True))
    notes_by_staff: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )

    ticket: "QueueTicket" = Relationship(back_populates="stages")
    service_point: "ServicePoint" = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[QueueTicketStage.service_point_id]"}
    )


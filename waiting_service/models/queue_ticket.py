
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

import sqlalchemy.dialects.postgresql as pg
from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.sql import func
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from models.queue_ticket_stage import QueueTicketStage
    from models.urgency_request import UrgencyRequest


class TicketStatus:
    WAITING   = "WAITING"
    ATTENDING = "ATTENDING"
    FINISHED  = "FINISHED"
    COMPLETED = "COMPLETED"
    PENDING   = "PENDING"
    CANCELLED = "CANCELLED"
    NO_SHOW   = "NO_SHOW"


class TicketPriority:
    NORMAL = 0
    HIGH   = 1
    URGENT = 2


class TicketChannel:
    KIOSK          = "KIOSK"
    SMS            = "SMS"
    APP            = "APP"
    STAFF_RECORDED = "STAFF_RECORDED"


class QueueTicket(SQLModel, table=True):
    """Core queue entry tracking a customer through one or more service points."""
    __tablename__ = "queue_tickets"
    __table_args__ = (
        Index("ix_qt_org_id",                   "org_id"),
        Index("ix_qt_flow_id",                  "flow_id"),
        Index("ix_qt_current_service_point_id", "current_service_point_id"),
        Index("ix_qt_status",                   "status"),
        Index("ix_qt_priority",                 "priority"),
        Index("ix_qt_created_at",               "created_at"),
        Index("ix_qt_external_id",              "external_id"),
    )

    id: uuid.UUID = Field(
        sa_column=Column(pg.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    )
    org_id: uuid.UUID = Field(sa_column=Column(pg.UUID(as_uuid=True), nullable=False, index=True))
    ticket_number: str = Field(sa_column=Column(String(50), nullable=False, unique=True, index=True))
    external_id: Optional[str] = Field(
        default=None, sa_column=Column(String(200), nullable=True, index=True)
    )
    phone_number: Optional[str] = Field(default=None, sa_column=Column(String(20), nullable=True))
    submitter_name: Optional[str] = Field(default=None, sa_column=Column(String(200), nullable=True))
    flow_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("service_flows.id", ondelete="RESTRICT"),
            nullable=False, index=True,
        )
    )
    current_service_point_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("service_points.id", ondelete="RESTRICT"),
            nullable=False, index=True,
        )
    )
    current_step_order: int = Field(default=1, sa_column=Column(Integer, nullable=False, default=1))
    status: str = Field(
        default=TicketStatus.WAITING,
        sa_column=Column(
            pg.ENUM("WAITING", "ATTENDING", "FINISHED", "COMPLETED", "PENDING", "CANCELLED", "NO_SHOW",
                    name="ticket_status"),
            nullable=False, index=True,
        ),
    )
    priority: int = Field(
        default=TicketPriority.NORMAL,
        sa_column=Column(Integer, nullable=False, default=0, index=True),
    )
    channel: str = Field(
        sa_column=Column(
            pg.ENUM("KIOSK", "SMS", "APP", "STAFF_RECORDED", name="ticket_channel"),
            nullable=False,
        )
    )
    notes: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    eta_minutes: Optional[float] = Field(default=None, sa_column=Column(Float, nullable=True))
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    )
    completed_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )

    stages: List["QueueTicketStage"] = Relationship(
        back_populates="ticket",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    urgency_requests: List["UrgencyRequest"] = Relationship(
        back_populates="ticket",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


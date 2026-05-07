
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

import sqlalchemy.dialects.postgresql as pg
from sqlalchemy import Column, DateTime, ForeignKey, Index, Text
from sqlalchemy.sql import func
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from models.queue_ticket import QueueTicket


class UrgencyType:
    MEDICAL        = "MEDICAL"
    FINANCIAL      = "FINANCIAL"
    TIME_SENSITIVE = "TIME_SENSITIVE"
    OTHER          = "OTHER"


class UrgencyStatus:
    PENDING  = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class UrgencyRequest(SQLModel, table=True):
    """Proof-backed request to escalate ticket priority to HIGH or URGENT."""
    __tablename__ = "urgency_requests"
    __table_args__ = (
        Index("ix_ur_ticket_id",    "ticket_id"),
        Index("ix_ur_org_id",       "org_id"),
        Index("ix_ur_status",       "status"),
        Index("ix_ur_urgency_type", "urgency_type"),
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
    org_id: uuid.UUID = Field(sa_column=Column(pg.UUID(as_uuid=True), nullable=False, index=True))
    requested_by_user_id: Optional[uuid.UUID] = Field(
        default=None, sa_column=Column(pg.UUID(as_uuid=True), nullable=True)
    )
    urgency_type: str = Field(
        sa_column=Column(
            pg.ENUM("MEDICAL", "FINANCIAL", "TIME_SENSITIVE", "OTHER", name="urgency_type"),
            nullable=False, index=True,
        )
    )
    evidence_notes: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    status: str = Field(
        default=UrgencyStatus.PENDING,
        sa_column=Column(
            pg.ENUM("PENDING", "APPROVED", "REJECTED", name="urgency_status"),
            nullable=False, default="PENDING", index=True,
        ),
    )
    reviewed_by_user_id: Optional[uuid.UUID] = Field(
        default=None, sa_column=Column(pg.UUID(as_uuid=True), nullable=True)
    )
    reviewed_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    reviewer_notes: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    requested_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )

    ticket: "QueueTicket" = Relationship(back_populates="urgency_requests")


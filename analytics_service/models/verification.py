"""models/verification.py — Verification scan analytics tables (populated from Kafka events)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Index, String
from sqlmodel import Field, SQLModel


class VerificationScanLog(SQLModel, table=True):
    """One row per verification.scanned event consumed from riviwa.verification.events."""

    __tablename__ = "verification_scan_logs"
    __table_args__ = (
        Index("ix_vsl_org_id",       "org_id"),
        Index("ix_vsl_product_id",   "product_id"),
        Index("ix_vsl_result",       "result"),
        Index("ix_vsl_scanned_at",   "scanned_at"),
    )

    id:          uuid.UUID = Field(primary_key=True)          # = verification_event_id from payload
    short_code:  str       = Field(sa_column=Column(String(130), nullable=False))
    result:      str       = Field(sa_column=Column(String(32),  nullable=False))  # AUTHENTIC / ALREADY_USED / UNRECOGNIZED
    org_id:      Optional[uuid.UUID] = Field(default=None)
    product_id:  Optional[uuid.UUID] = Field(default=None)
    qr_type:     Optional[str]       = Field(default=None, sa_column=Column(String(32),  nullable=True))
    scanner_lat: Optional[float]     = Field(default=None)
    scanner_lng: Optional[float]     = Field(default=None)
    scanned_at:  datetime            = Field(index=True)


class VerificationFakeReportLog(SQLModel, table=True):
    """One row per verification.fake_reported event consumed from riviwa.verification.events."""

    __tablename__ = "verification_fake_report_logs"
    __table_args__ = (
        Index("ix_vfrl_org_id",      "org_id"),
        Index("ix_vfrl_reported_at", "reported_at"),
    )

    id:                    uuid.UUID        = Field(primary_key=True)   # = report_id from payload
    verification_event_id: uuid.UUID        = Field(index=True)
    short_code:            str              = Field(sa_column=Column(String(130), nullable=False))
    org_id:                Optional[uuid.UUID] = Field(default=None)
    has_photo:             bool             = Field(default=False)
    gps_lat:               Optional[float]  = Field(default=None)
    gps_lng:               Optional[float]  = Field(default=None)
    reported_at:           datetime         = Field(index=True)

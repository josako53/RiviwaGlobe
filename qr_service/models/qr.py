"""models/qr.py — QR code, receipt session, scan, and batch ORM models."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class QRCode(SQLModel, table=True):
    __tablename__ = "qr_codes"

    id:               uuid.UUID        = Field(default_factory=uuid.uuid4, primary_key=True)
    short_code:       str              = Field(max_length=16, unique=True, index=True)
    sms_code:         str              = Field(max_length=64, unique=True, index=True,
                                               description="{ORG_SMS_CODE}-{SHORT_CODE}")
    qr_type:          str              = Field(sa_column=Column(String(32), nullable=False, index=True))
    organisation_id:  uuid.UUID        = Field(index=True)
    org_sms_code:     Optional[str]    = Field(default=None, max_length=10, index=True,
                                               description="Org's registered SMS prefix (UTT, CRDB …)")

    # Context links (soft, no DB-level FK across service boundaries)
    project_id:          Optional[uuid.UUID] = Field(default=None, nullable=True)
    service_id:          Optional[uuid.UUID] = Field(default=None, nullable=True)
    product_id:          Optional[uuid.UUID] = Field(default=None, nullable=True)
    receipt_session_id:  Optional[uuid.UUID] = Field(default=None, nullable=True, index=True)

    # QR artefacts
    redirect_url:    str              = Field(max_length=2048)
    qr_image_key:    Optional[str]    = Field(default=None, max_length=512)
    qr_image_url:    Optional[str]    = Field(default=None, max_length=2048)

    # State
    scan_count:  int  = Field(default=0)
    is_active:   bool = Field(default=True, index=True)

    # Bulk batch reference
    batch_id:   Optional[uuid.UUID] = Field(default=None, nullable=True, index=True)

    # Permanent — no time-based expiry. Only marked used when feedback submitted.
    expires_at: Optional[datetime] = Field(default=None, nullable=True)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class QRScan(SQLModel, table=True):
    __tablename__ = "qr_scans"

    id:                 uuid.UUID        = Field(default_factory=uuid.uuid4, primary_key=True)
    qr_code_id:         uuid.UUID        = Field(index=True)
    short_code:         str              = Field(max_length=64, index=True)
    organisation_id:    uuid.UUID        = Field(index=True)
    qr_type:            str              = Field(max_length=20)
    scanner_ip:         Optional[str]    = Field(default=None, max_length=64)
    scanner_ua:         Optional[str]    = Field(default=None, max_length=512)
    fingerprint:        Optional[str]    = Field(default=None, max_length=32)
    feedback_submitted: bool             = Field(default=False, index=True)
    feedback_id:        Optional[uuid.UUID] = Field(default=None, nullable=True)
    scanned_at:         datetime         = Field(default_factory=datetime.utcnow, index=True)


class ReceiptSession(SQLModel, table=True):
    """
    One row per receipt issued by a third-party.
    Permanent — no expiry. is_consumed set True only when feedback submitted.
    """
    __tablename__ = "receipt_sessions"

    id:                   uuid.UUID        = Field(default_factory=uuid.uuid4, primary_key=True)
    organisation_id:      uuid.UUID        = Field(index=True)
    consumer_phone:       Optional[str]    = Field(default=None, max_length=32)
    consumer_name:        Optional[str]    = Field(default=None, max_length=128)
    service_name:         Optional[str]    = Field(default=None, max_length=256)
    department:           Optional[str]    = Field(default=None, max_length=128)
    attendant_name:       Optional[str]    = Field(default=None, max_length=128)
    location:             Optional[str]    = Field(default=None, max_length=512)
    transaction_datetime: Optional[str]    = Field(default=None, max_length=64)
    receipt_number:       Optional[str]    = Field(default=None, max_length=64)
    amount:               Optional[float]  = Field(default=None, nullable=True)
    currency:             Optional[str]    = Field(default=None, max_length=8)
    custom_attributes:    Optional[Any]    = Field(default=None, sa_column=Column(JSONB, nullable=True))
    is_consumed:          bool             = Field(default=False, index=True)
    expires_at:           Optional[datetime] = Field(default=None, nullable=True)
    created_at:           datetime         = Field(default_factory=datetime.utcnow)


class QRBatch(SQLModel, table=True):
    """Bulk product QR generation job — generates N QR codes and packages them as ZIP."""
    __tablename__ = "qr_batches"

    id:               uuid.UUID        = Field(default_factory=uuid.uuid4, primary_key=True)
    organisation_id:  uuid.UUID        = Field(index=True)
    product_id:       Optional[uuid.UUID] = Field(default=None, nullable=True)
    qr_type:          str              = Field(sa_column=Column(String(32), nullable=False))
    count:            int              = Field(ge=1, le=10000)
    label:            Optional[str]    = Field(default=None, max_length=256)
    title:            Optional[str]    = Field(default=None, max_length=256)
    brand:            Optional[str]    = Field(default=None, max_length=128)
    rsin:             Optional[str]    = Field(default=None, max_length=32)
    status:           str              = Field(
        default="PENDING",
        sa_column=Column(String(20), nullable=False, index=True),
    )
    generated_count:  int              = Field(default=0)
    zip_key:          Optional[str]    = Field(default=None, max_length=512)
    zip_url:          Optional[str]    = Field(default=None, max_length=2048)
    error_message:    Optional[str]    = Field(default=None, max_length=1024)
    created_at:       datetime         = Field(default_factory=datetime.utcnow)
    completed_at:     Optional[datetime] = Field(default=None, nullable=True)

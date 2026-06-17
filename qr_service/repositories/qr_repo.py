"""repositories/qr_repo.py — QR code database operations."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional, Tuple

import structlog
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.qr import QRBatch, QRCode, QRScan, ReceiptSession

log = structlog.get_logger(__name__)

_QR_UPDATABLE = frozenset({
    "redirect_url", "product_id", "service_id", "project_id",
    "branch_id", "department_id", "label", "is_active",
})


class QRRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── QRCode CRUD ───────────────────────────────────────────────────────────

    async def create(self, qr: QRCode) -> QRCode:
        self.db.add(qr)
        await self.db.flush()
        return qr

    async def get_by_id(self, qr_id: uuid.UUID) -> Optional[QRCode]:
        return await self.db.get(QRCode, qr_id)

    async def get_by_short_code(self, short_code: str) -> Optional[QRCode]:
        result = await self.db.execute(
            select(QRCode).where(QRCode.short_code == short_code.upper())
        )
        return result.scalar_one_or_none()

    async def get_by_sms_code(self, sms_code: str) -> Optional[QRCode]:
        result = await self.db.execute(
            select(QRCode).where(QRCode.sms_code == sms_code.upper())
        )
        return result.scalar_one_or_none()

    async def resolve(self, raw_code: str) -> Optional[QRCode]:
        """
        Resolve a code in any of these formats:
          - XXXXXX                    (bare short code)
          - UTT-XXXXXX                ({ORG_SMS_CODE}-{SHORT_CODE})
          - UTT XXXXXX                (space-separated SMS text)
          - https://…/qr/XXXXXX       (full QR URL)
        """
        code = raw_code.strip().upper()
        if "/qr/" in code:
            code = code.split("/qr/")[-1].split("?")[0].strip()
        # Normalise space-separated SMS format: "YAS-TANZANIA Y8JU8PQJ" -> "YAS-TANZANIA-Y8JU8PQJ"
        # Use short_code length (8) to identify the split point, not prefix length limit.
        if " " in code:
            parts = code.split(None, 1)
            if len(parts) == 2 and len(parts[1]) == 8:
                code = f"{parts[0]}-{parts[1]}"
        if "-" in code:
            by_sms = await self.get_by_sms_code(code)
            if by_sms:
                return by_sms
            # Extract short_code as the last 8-char segment after the final hyphen.
            # Works for both "UTT-XXXXXX" and "YAS-TANZANIA-XXXXXX".
            short_part = code.rsplit("-", 1)[-1]
            if len(short_part) == 8:
                return await self.get_by_short_code(short_part)
            return None
        return await self.get_by_short_code(code)

    async def list_by_org(
        self,
        org_id:        Optional[uuid.UUID] = None,
        qr_type:       Optional[str]       = None,
        product_id:    Optional[uuid.UUID] = None,
        service_id:    Optional[uuid.UUID] = None,
        project_id:    Optional[uuid.UUID] = None,
        branch_id:     Optional[uuid.UUID] = None,
        department_id: Optional[uuid.UUID] = None,
        batch_id:      Optional[uuid.UUID] = None,
        is_active:     Optional[bool]      = True,
        page:          int = 1,
        size:          int = 20,
    ) -> Tuple[List[QRCode], int]:
        q = select(QRCode)
        if org_id:
            q = q.where(QRCode.organisation_id == org_id)
        if is_active is not None:
            q = q.where(QRCode.is_active == is_active)
        if qr_type:
            q = q.where(QRCode.qr_type == qr_type.upper())
        if product_id:
            q = q.where(QRCode.product_id == product_id)
        if service_id:
            q = q.where(QRCode.service_id == service_id)
        if project_id:
            q = q.where(QRCode.project_id == project_id)
        if branch_id:
            q = q.where(QRCode.branch_id == branch_id)
        if department_id:
            q = q.where(QRCode.department_id == department_id)
        if batch_id:
            q = q.where(QRCode.batch_id == batch_id)
        total = (await self.db.execute(
            select(func.count()).select_from(q.subquery())
        )).scalar_one()
        items = (await self.db.execute(
            q.order_by(QRCode.created_at.desc()).offset((page - 1) * size).limit(size)
        )).scalars().all()
        return list(items), total

    async def update_qr(self, qr: QRCode, **fields) -> QRCode:
        """Update allowed fields only. Ignores unknown keys."""
        for key, value in fields.items():
            if key in _QR_UPDATABLE:
                setattr(qr, key, value)
        qr.updated_at = datetime.utcnow()
        self.db.add(qr)
        await self.db.flush()
        return qr

    async def increment_scan(self, qr_id: uuid.UUID) -> None:
        await self.db.execute(
            update(QRCode)
            .where(QRCode.id == qr_id)
            .values(scan_count=QRCode.scan_count + 1, updated_at=datetime.utcnow())
        )

    async def deactivate(self, qr: QRCode) -> None:
        qr.is_active = False
        qr.updated_at = datetime.utcnow()
        self.db.add(qr)
        await self.db.flush()

    # ── Feedback marking ──────────────────────────────────────────────────────

    async def has_feedback(
        self, qr_id: uuid.UUID, receipt_session_id: Optional[uuid.UUID]
    ) -> Tuple[bool, Optional[uuid.UUID]]:
        scan = (await self.db.execute(
            select(QRScan)
            .where(QRScan.qr_code_id == qr_id, QRScan.feedback_submitted == True)
            .order_by(QRScan.scanned_at.desc())
            .limit(1)
        )).scalar_one_or_none()
        if scan:
            return True, scan.feedback_id
        if receipt_session_id:
            session = await self.db.get(ReceiptSession, receipt_session_id)
            if session and session.is_consumed:
                return True, None
        return False, None

    async def mark_feedback(
        self,
        short_code: str,
        feedback_id: Optional[uuid.UUID] = None,
    ) -> bool:
        qr = await self.resolve(short_code)
        if not qr:
            log.warning("qr_repo.mark_feedback.not_found", code=short_code)
            return False
        await self.db.execute(
            update(QRScan)
            .where(QRScan.qr_code_id == qr.id, QRScan.feedback_submitted == False)
            .values(feedback_submitted=True, feedback_id=feedback_id)
        )
        if qr.receipt_session_id:
            session = await self.db.get(ReceiptSession, qr.receipt_session_id)
            if session:
                session.is_consumed = True
                self.db.add(session)
        qr.updated_at = datetime.utcnow()
        self.db.add(qr)
        await self.db.flush()
        log.info("qr_repo.mark_feedback.done", short_code=short_code, feedback_id=str(feedback_id or ""))
        return True

    # ── Scan recording ────────────────────────────────────────────────────────

    async def record_scan(
        self,
        qr_id:           uuid.UUID,
        short_code:      str,
        organisation_id: Optional[uuid.UUID] = None,
        qr_type:         str = "",
        ip:              Optional[str] = None,
        ua:              Optional[str] = None,
        fingerprint:     Optional[str] = None,
    ) -> QRScan:
        scan = QRScan(
            qr_code_id=qr_id,
            short_code=short_code,
            organisation_id=organisation_id,
            qr_type=qr_type,
            scanner_ip=ip,
            scanner_ua=(ua or "")[:512],
            fingerprint=fingerprint,
        )
        self.db.add(scan)
        await self.db.flush()
        return scan

    async def list_scans(
        self,
        qr_id:              uuid.UUID,
        feedback_submitted: Optional[bool] = None,
        page:               int = 1,
        size:               int = 20,
    ) -> Tuple[List[QRScan], int]:
        q = select(QRScan).where(QRScan.qr_code_id == qr_id)
        if feedback_submitted is not None:
            q = q.where(QRScan.feedback_submitted == feedback_submitted)
        total = (await self.db.execute(
            select(func.count()).select_from(q.subquery())
        )).scalar_one()
        items = (await self.db.execute(
            q.order_by(QRScan.scanned_at.desc()).offset((page - 1) * size).limit(size)
        )).scalars().all()
        return list(items), total

    # ── Scan analytics ────────────────────────────────────────────────────────

    async def scan_analytics(self, org_id: Optional[uuid.UUID] = None) -> dict:
        q = select(QRCode.id)
        if org_id:
            q = q.where(QRCode.organisation_id == org_id)
        qr_ids = (await self.db.execute(q)).scalars().all()
        if not qr_ids:
            return {"total_scans": 0, "unique_scanners": 0, "converted": 0, "conversion_rate": 0.0}
        return await self._scan_stats(QRScan.qr_code_id.in_(qr_ids))

    async def scan_analytics_for_qr(self, qr_id: uuid.UUID) -> dict:
        return await self._scan_stats(QRScan.qr_code_id == qr_id)

    async def _scan_stats(self, where_clause) -> dict:
        total = (await self.db.execute(
            select(func.count(QRScan.id)).where(where_clause)
        )).scalar_one()
        unique = (await self.db.execute(
            select(func.count(func.distinct(QRScan.fingerprint)))
            .where(where_clause, QRScan.fingerprint.isnot(None))
        )).scalar_one()
        converted = (await self.db.execute(
            select(func.count(QRScan.id)).where(where_clause, QRScan.feedback_submitted == True)
        )).scalar_one()
        return {
            "total_scans":     total,
            "unique_scanners": unique,
            "converted":       converted,
            "conversion_rate": round(converted / total * 100, 2) if total else 0.0,
        }

    # ── Receipt session ───────────────────────────────────────────────────────

    async def create_receipt_session(self, session: ReceiptSession) -> ReceiptSession:
        self.db.add(session)
        await self.db.flush()
        return session

    async def get_receipt_session(self, session_id: uuid.UUID) -> Optional[ReceiptSession]:
        return await self.db.get(ReceiptSession, session_id)

    async def list_receipt_sessions(
        self,
        org_id:      uuid.UUID,
        is_consumed: Optional[bool] = None,
        page:        int = 1,
        size:        int = 20,
    ) -> Tuple[List[ReceiptSession], int]:
        q = select(ReceiptSession).where(ReceiptSession.organisation_id == org_id)
        if is_consumed is not None:
            q = q.where(ReceiptSession.is_consumed == is_consumed)
        total = (await self.db.execute(
            select(func.count()).select_from(q.subquery())
        )).scalar_one()
        items = (await self.db.execute(
            q.order_by(ReceiptSession.created_at.desc()).offset((page - 1) * size).limit(size)
        )).scalars().all()
        return list(items), total

    # ── QR batch ──────────────────────────────────────────────────────────────

    async def create_batch(self, batch: QRBatch) -> QRBatch:
        self.db.add(batch)
        await self.db.flush()
        return batch

    async def get_batch(self, batch_id: uuid.UUID) -> Optional[QRBatch]:
        return await self.db.get(QRBatch, batch_id)

    async def list_batches(
        self,
        org_id:  Optional[uuid.UUID] = None,
        qr_type: Optional[str] = None,
        status:  Optional[str] = None,
        page:    int = 1,
        size:    int = 20,
    ) -> Tuple[List[QRBatch], int]:
        q = select(QRBatch)
        if org_id:
            q = q.where(QRBatch.organisation_id == org_id)
        if qr_type:
            q = q.where(QRBatch.qr_type == qr_type.upper())
        if status:
            q = q.where(QRBatch.status == status.upper())
        total = (await self.db.execute(
            select(func.count()).select_from(q.subquery())
        )).scalar_one()
        items = (await self.db.execute(
            q.order_by(QRBatch.created_at.desc()).offset((page - 1) * size).limit(size)
        )).scalars().all()
        return list(items), total

    async def update_batch(self, batch: QRBatch, **kwargs) -> QRBatch:
        for k, v in kwargs.items():
            setattr(batch, k, v)
        self.db.add(batch)
        await self.db.flush()
        return batch

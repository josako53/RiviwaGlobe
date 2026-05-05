"""api/v1/stats.py — Verification analytics, heatmap, and stats."""
from __future__ import annotations
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import JWTDep
from db.session import get_async_session
from models.verification import FakeSuspectReport, UnrecognizedScanHeatmap, VerificationEvent

router = APIRouter(prefix="/api/v1/verify", tags=["Verification — Stats"])


@router.get("/stats", status_code=200)
async def get_stats(
    organisation_id: Optional[uuid.UUID] = Query(default=None),
    from_date: Optional[str] = Query(default=None),
    to_date: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_async_session),
    _claims = JWTDep,
) -> dict:
    """Aggregate verification statistics — counts by result and fake report breakdown."""
    from_dt = datetime.fromisoformat(from_date) if from_date else datetime.utcnow() - timedelta(days=30)
    to_dt   = datetime.fromisoformat(to_date)   if to_date   else datetime.utcnow()

    q = select(VerificationEvent.result, func.count(VerificationEvent.id)).where(
        VerificationEvent.verified_at >= from_dt,
        VerificationEvent.verified_at <= to_dt,
    )
    if organisation_id:
        q = q.where(VerificationEvent.organisation_id == organisation_id)
    q = q.group_by(VerificationEvent.result)
    rows = (await db.execute(q)).all()

    counts = {r: 0 for r in ("AUTHENTIC", "ALREADY_USED", "UNRECOGNIZED")}
    for result, cnt in rows:
        counts[result] = cnt
    total = sum(counts.values())

    # Fake report breakdown
    rq = select(FakeSuspectReport.status, func.count(FakeSuspectReport.id)).group_by(FakeSuspectReport.status)
    if organisation_id:
        rq = rq.where(FakeSuspectReport.organisation_id == organisation_id)
    report_rows = (await db.execute(rq)).all()

    return {
        "period": {"from": from_dt.isoformat(), "to": to_dt.isoformat()},
        "total_verifications": total,
        "authentic_count": counts["AUTHENTIC"],
        "already_used_count": counts["ALREADY_USED"],
        "unrecognized_count": counts["UNRECOGNIZED"],
        "genuine_rate": round(counts["AUTHENTIC"] / total * 100, 2) if total else 0,
        "fake_reports": {status: count for status, count in report_rows},
    }


@router.get("/heatmap", status_code=200)
async def get_heatmap(
    organisation_id: Optional[uuid.UUID] = Query(default=None),
    from_date: Optional[str] = Query(default=None),
    to_date: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_async_session),
    _claims = JWTDep,
) -> dict:
    """
    Returns GPS points and cluster cells for all UNRECOGNIZED scans.
    Use this to visualise where suspected counterfeit products are circulating.
    """
    from_dt = datetime.fromisoformat(from_date) if from_date else datetime.utcnow() - timedelta(days=30)
    to_dt   = datetime.fromisoformat(to_date)   if to_date   else datetime.utcnow()

    q = select(UnrecognizedScanHeatmap).where(
        UnrecognizedScanHeatmap.recorded_at >= from_dt,
        UnrecognizedScanHeatmap.recorded_at <= to_dt,
    )
    points = (await db.execute(q)).scalars().all()

    # Aggregate by cluster cell
    cluster_counts: dict = {}
    raw_points = []
    for p in points:
        raw_points.append({"lat": float(p.lat), "lng": float(p.lng), "at": p.recorded_at.isoformat()})
        cell = p.cluster_cell or f"{round(float(p.lat), 1)},{round(float(p.lng), 1)}"
        cluster_counts[cell] = cluster_counts.get(cell, 0) + 1

    clusters = [{"cell": cell, "count": cnt, "lat": float(cell.split(",")[0]), "lng": float(cell.split(",")[1])}
                for cell, cnt in sorted(cluster_counts.items(), key=lambda x: -x[1])]

    return {
        "total_points": len(raw_points),
        "points": raw_points[:500],   # cap at 500 for response size
        "clusters": clusters[:100],
        "period": {"from": from_dt.isoformat(), "to": to_dt.isoformat()},
    }

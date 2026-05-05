"""api/v1/public.py — Public QR scan endpoint (no auth)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import fingerprint
from db.session import get_async_session
from repositories.qr_repo import QRRepository

router = APIRouter(tags=["QR — Public"])


@router.get("/qr/{short_code}", include_in_schema=False)
async def public_scan(
    short_code: str,
    request: Request,
    db: AsyncSession = Depends(get_async_session),
) -> RedirectResponse:
    """
    Public QR scan endpoint — hit when a consumer scans a printed QR code.
    Records the scan event and redirects (302) to the Riviwa feedback app.
    No auth required — this is the consumer-facing entry point.

    QR codes are PERMANENT EVIDENCE. They never expire on time.
    They are only marked ALREADY_USED when feedback is actually submitted.
    """
    repo = QRRepository(db)
    qr = await repo.resolve(short_code)

    if not qr or not qr.is_active:
        # Redirect to an "unrecognized" page rather than 404
        from core.config import settings
        return RedirectResponse(
            url=f"{settings.FEEDBACK_APP_URL}/verify?code={short_code}&result=unrecognized",
            status_code=302,
        )

    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent", "")
    fp = fingerprint(ip or "", ua)

    await repo.record_scan(qr.id, qr.short_code, ip=ip, ua=ua, fingerprint=fp)
    await repo.increment_scan(qr.id)
    await db.commit()

    return RedirectResponse(url=qr.redirect_url, status_code=302)

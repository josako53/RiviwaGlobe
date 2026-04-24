"""
api/v1/context.py — Context session endpoints.

Partners push pre-filled user context BEFORE the user launches a Riviwa
mini-app, widget, or chatbot. The session token is then passed as a URL
parameter so Riviwa can pre-fill feedback fields without asking again.

Flow:
  1. Partner server → POST /integration/context  { phone, name, service_id, ... }
  2. Riviwa returns { session_token }  (shown once, valid 30 min)
  3. Partner opens Riviwa widget/mini-app with ?session_token=<token>
  4. Riviwa widget calls GET /integration/context/consume?token=<token>
  5. Pre-fill data decrypted and returned; session consumed (single-use)
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import IntegrationAuthDep, AuthContext
from core.config import settings
from core.security import (
    encrypt_field, decrypt_field,
    generate_opaque_token, hash_code,
)
from db.session import get_async_session
from models.integration import ContextSession

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/integration/context", tags=["Integration — Context Sessions"])


# ── POST /integration/context — Partner pushes pre-fill data ─────────────────

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_context_session(
    body: dict,
    db: AsyncSession = Depends(get_async_session),
    ctx: AuthContext = IntegrationAuthDep,
) -> dict:
    """
    Partner pushes user context before launching a Riviwa widget or mini-app.

    Body fields (all optional except at least one must be present):
      phone        — user phone number (E.164 format recommended)
      name         — user full name
      email        — user email
      account_ref  — partner's internal account/customer reference
      service_id   — Riviwa service UUID to pre-select
      product_id   — Riviwa product UUID to pre-select
      category_id  — Riviwa feedback category UUID
      department_id — Riviwa department UUID
      project_id   — Restrict session to a specific Riviwa project
      org_id       — Restricts session to a specific organisation
      ttl_seconds  — Override default 30-minute TTL (max 3600)
      metadata     — Freeform dict for partner-specific data

    Returns session_token (shown once) that the partner passes to the widget.
    """
    ctx.require_scope("data:push")

    # Validate at least one identifying field is present
    id_fields = {"phone", "name", "email", "account_ref"}
    if not any(body.get(f) for f in id_fields):
        raise HTTPException(
            status_code=400,
            detail={"error": "MISSING_CONTEXT_DATA",
                    "message": "Provide at least one of: phone, name, email, account_ref"},
        )

    ttl = min(int(body.get("ttl_seconds", settings.CONTEXT_SESSION_TTL_SECONDS)), 3600)
    expires_at = datetime.utcnow() + timedelta(seconds=ttl)

    # Encrypt the pre-fill payload
    pre_fill = {k: body[k] for k in [
        "phone", "name", "email", "account_ref",
        "service_id", "product_id", "category_id",
        "department_id", "metadata",
    ] if k in body}
    encrypted = encrypt_field(json.dumps(pre_fill))

    raw_token, token_hash = generate_opaque_token(32)

    session = ContextSession(
        client_id           = ctx.client.id,
        token_hash          = token_hash,
        pre_filled_data_enc = encrypted,
        project_id          = uuid.UUID(body["project_id"]) if body.get("project_id") else None,
        org_id              = uuid.UUID(body["org_id"])     if body.get("org_id")     else None,
        expires_at          = expires_at,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    log.info("integration.context_session_created",
             client_id=str(ctx.client.id), session_id=str(session.id))

    return {
        "session_token": raw_token,
        "session_id":    str(session.id),
        "expires_at":    expires_at.isoformat(),
        "ttl_seconds":   ttl,
        "warning":       "Store session_token securely — it will not be shown again.",
    }


# ── GET /integration/context/consume — Widget consumes context ───────────────

@router.get("/consume")
async def consume_context_session(
    token: str,
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """
    Called by the Riviwa widget/mini-app to retrieve and consume pre-fill data.

    The session_token passed as ?token= is single-use and expires in 30 min.
    After consumption, consumed_at is set and the session cannot be reused.
    """
    from sqlalchemy import select
    token_hash = hash_code(token)

    result = await db.execute(
        select(ContextSession).where(
            ContextSession.token_hash  == token_hash,
            ContextSession.consumed_at.is_(None),
        )
    )
    session = result.scalars().first()
    if not session:
        raise HTTPException(
            status_code=404,
            detail={"error": "SESSION_NOT_FOUND",
                    "message": "Token is invalid, expired, or already consumed"},
        )
    if session.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=410,
            detail={"error": "SESSION_EXPIRED"},
        )

    # Decrypt pre-fill data
    try:
        pre_fill = json.loads(decrypt_field(session.pre_filled_data_enc))
    except Exception:
        raise HTTPException(500, {"error": "DECRYPTION_FAILED"})

    # Mark consumed (single-use)
    session.consumed_at = datetime.utcnow()
    await db.commit()

    return {
        "session_id":  str(session.id),
        "project_id":  str(session.project_id) if session.project_id else None,
        "org_id":      str(session.org_id)      if session.org_id     else None,
        "pre_fill":    pre_fill,
    }


# ── GET /integration/context/{session_id} — Check session status ─────────────

@router.get("/{session_id}")
async def get_context_session_status(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
    ctx: AuthContext = IntegrationAuthDep,
) -> dict:
    """
    Check the status of a context session (without consuming it).
    Partners can use this to verify if a session is still active.
    """
    session = await db.get(ContextSession, session_id)
    if not session or session.client_id != ctx.client.id:
        raise HTTPException(404, {"error": "SESSION_NOT_FOUND"})

    return {
        "session_id":   str(session.id),
        "is_consumed":  session.consumed_at is not None,
        "is_expired":   session.expires_at < datetime.utcnow(),
        "project_id":   str(session.project_id) if session.project_id else None,
        "org_id":       str(session.org_id)      if session.org_id     else None,
        "expires_at":   session.expires_at.isoformat(),
        "consumed_at":  session.consumed_at.isoformat() if session.consumed_at else None,
        "created_at":   session.created_at.isoformat(),
    }

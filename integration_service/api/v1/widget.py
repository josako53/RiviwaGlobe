"""
api/v1/widget.py — Widget and mini-app session management.

All widget sessions are org-scoped. The client's bound organisation_id
is automatically injected — the frontend never needs to supply it.

Two embed modes:
  1. JS Widget / Tag  — partner embeds <script> tag; JS calls this API
  2. Mini App         — partner mobile app opens a Riviwa WebView
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import IntegrationAuthDep, AuthContext
from core.config import settings
from core.security import encrypt_field, decrypt_field, generate_opaque_token, hash_code
from db.session import get_async_session
from models.integration import ContextSession, IntegrationClient

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/integration/widget", tags=["Integration — Widget & Mini App"])


def _check_origin(client: IntegrationClient, origin: Optional[str]) -> bool:
    if not client.allowed_origins:
        return False
    if "*" in client.allowed_origins:
        return True
    return origin in client.allowed_origins if origin else False


# ── POST /integration/widget/session — Create widget session ─────────────────

@router.post("/session", status_code=status.HTTP_201_CREATED)
async def create_widget_session(
    body: dict,
    db: AsyncSession = Depends(get_async_session),
    ctx: AuthContext = IntegrationAuthDep,
) -> dict:
    """
    Create a widget/mini-app embed session. Automatically scoped to the
    client's bound organisation_id — no need to pass org_id in the body.

    Body:
      user_ref      — partner's user ID / reference (opaque to Riviwa)
      project_id    — lock widget to a specific Riviwa project (optional)
      context_token — pre-existing context session token (optional)
      ttl_seconds   — session TTL override (default 30 min, max 2 hours)
      locale        — UI locale hint, e.g. "sw" or "en"
      theme         — "light" | "dark" | "auto"

    Returns embed_token + org_id so the widget auto-configures for the right org.
    """
    ctx.require_scope("feedback:write")
    org_id = ctx.validate_org(
        uuid.UUID(body["org_id"]) if body.get("org_id") else None
    )

    ttl = min(int(body.get("ttl_seconds", 1800)), 7200)
    expires_at = datetime.utcnow() + timedelta(seconds=ttl)

    config = {
        "user_ref":      body.get("user_ref"),
        "context_token": body.get("context_token"),
        "locale":        body.get("locale", "en"),
        "theme":         body.get("theme", "light"),
        "_widget":       True,
    }
    encrypted = encrypt_field(json.dumps(config))
    raw_token, token_hash = generate_opaque_token(32)

    session = ContextSession(
        client_id           = ctx.client.id,
        token_hash          = token_hash,
        pre_filled_data_enc = encrypted,
        project_id          = uuid.UUID(body["project_id"]) if body.get("project_id") else None,
        org_id              = org_id,
        expires_at          = expires_at,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    log.info("integration.widget_session_created",
             client_id=str(ctx.client.id), org_id=str(org_id))

    return {
        "embed_token":  raw_token,
        "session_id":   str(session.id),
        "org_id":       str(org_id),
        "project_id":   str(session.project_id) if session.project_id else None,
        "expires_at":   expires_at.isoformat(),
        "ttl_seconds":  ttl,
        "embed_url":    f"{settings.RIVIWA_WIDGET_BASE_URL}/embed?token={raw_token}&org={org_id}",
        "warning":      "embed_token is single-use and expires in the ttl specified.",
    }


# ── GET /integration/widget/config — Widget JS fetches config ────────────────

@router.get("/config")
async def get_widget_config(
    request: Request,
    client_id: str,
    token: Optional[str] = None,
    db: AsyncSession = Depends(get_async_session),
) -> JSONResponse:
    """
    Called by the embedded JS widget to fetch runtime configuration.
    Checks Origin header against allowed_origins. Returns org_id so the
    widget knows which organisation's projects/categories to display.
    """
    origin = request.headers.get("origin")
    result = await db.execute(
        select(IntegrationClient).where(
            IntegrationClient.client_id == client_id,
            IntegrationClient.is_active == True,
        )
    )
    client = result.scalars().first()
    if not client:
        raise HTTPException(404, {"error": "CLIENT_NOT_FOUND"})

    if not _check_origin(client, origin):
        raise HTTPException(
            status_code=403,
            detail={"error": "ORIGIN_NOT_ALLOWED",
                    "message": f"Origin '{origin}' is not in the allowed_origins list"},
        )

    config = {
        "client_id":     client.client_id,
        "client_name":   client.name,
        "environment":   client.environment,
        "org_id":        str(client.organisation_id) if client.organisation_id else None,
        "scopes":        client.allowed_scopes,
        "require_auth":  "feedback:write" in client.allowed_scopes,
    }

    if token:
        token_hash = hash_code(token)
        sc_result = await db.execute(
            select(ContextSession).where(
                ContextSession.token_hash  == token_hash,
                ContextSession.consumed_at.is_(None),
            )
        )
        sess = sc_result.scalars().first()
        if sess and sess.expires_at > datetime.utcnow():
            try:
                pre_fill = json.loads(decrypt_field(sess.pre_filled_data_enc))
                if not pre_fill.get("_widget"):
                    config["pre_fill"] = pre_fill
                # Always surface the session's org_id (authoritative)
                if sess.org_id:
                    config["org_id"] = str(sess.org_id)
                if sess.project_id:
                    config["project_id"] = str(sess.project_id)
            except Exception:
                pass

    headers = {
        "Access-Control-Allow-Origin": origin or "*",
        "Access-Control-Allow-Credentials": "true",
        "Vary": "Origin",
    }
    return JSONResponse(content=config, headers=headers)


# ── GET /integration/widget/snippet — JS tag snippet ─────────────────────────

@router.get("/snippet")
async def get_embed_snippet(
    client_id: str,
    db: AsyncSession = Depends(get_async_session),
    ctx: AuthContext = IntegrationAuthDep,
) -> dict:
    """
    Returns the copy-paste JS snippet for website embedding.
    The snippet bakes in the org_id so every page-view is auto-scoped.
    """
    result = await db.execute(
        select(IntegrationClient).where(
            IntegrationClient.client_id == client_id,
            IntegrationClient.is_active == True,
        )
    )
    client = result.scalars().first()
    if not client or client.id != ctx.client.id:
        raise HTTPException(404, {"error": "CLIENT_NOT_FOUND"})

    org_id = str(client.organisation_id) if client.organisation_id else "null"
    base   = settings.RIVIWA_WIDGET_BASE_URL

    snippet = (
        "<!-- Riviwa Feedback Widget -->\n"
        "<script>\n"
        "  (function(r,i,v,i2,w,a){{r['RiviwaObject']=w;r[w]=r[w]||function(){{}}\n"
        "  ;(r[w].q=r[w].q||[]).push(arguments)}},r[w].l=1*new Date();a=i.createElement(v),\n"
        "  m=i.getElementsByTagName(v)[0];a.async=1;a.src=i2;m.parentNode.insertBefore(a,m)\n"
        f"  }})(window,document,'script','{base}/widget.js','riviwa');\n"
        f"  riviwa('init', '{client_id}', {{org: '{org_id}'}});\n"
        "  riviwa('track', 'page_view');\n"
        "</script>\n"
        "<!-- End Riviwa Feedback Widget -->"
    )

    return {
        "client_id": client_id,
        "org_id":    org_id,
        "snippet":   snippet,
        "widget_js": f"{base}/widget.js",
        "docs_url":  "https://docs.riviwa.com/integration/widget",
    }

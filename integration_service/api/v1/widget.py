"""
api/v1/widget.py — Widget and mini-app session management.

Two embed modes:
  1. JS Widget / Tag  — partner embeds <script> tag; JS calls this API
  2. Mini App         — partner mobile app opens a Riviwa WebView

Widget session lifecycle:
  1. POST /integration/widget/session   — partner backend creates widget session
  2. GET  /integration/widget/config    — JS widget fetches config (CORS-checked)
  3. User completes feedback in widget
  4. Riviwa fires webhook to partner on feedback.submitted event
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse

import json

from core.auth import IntegrationAuthDep, AuthContext
from core.config import settings
from core.security import encrypt_field, decrypt_field, generate_opaque_token, hash_code
from db.session import get_async_session
from models.integration import ContextSession, IntegrationClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/integration/widget", tags=["Integration — Widget & Mini App"])


def _check_origin(client: IntegrationClient, origin: Optional[str]) -> bool:
    if not client.allowed_origins:
        return False  # no allowed origins = block all cross-origin
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
    Create a widget/mini-app embed session.

    Called from the partner's **backend** to generate a signed session
    that the frontend widget uses to authenticate itself.

    Body:
      user_ref      — partner's user ID / reference (opaque to Riviwa)
      project_id    — lock widget to a specific Riviwa project (optional)
      org_id        — lock widget to a specific org (optional)
      context_token — pre-existing context session token (optional)
      ttl_seconds   — session TTL override (default 30 min, max 2 hours)
      locale        — UI locale hint, e.g. "sw" or "en" (optional)
      theme         — "light" | "dark" | "auto" (optional)

    Returns embed_token used by the frontend widget.
    """
    ctx.require_scope("feedback:write")

    ttl = min(int(body.get("ttl_seconds", 1800)), 7200)
    expires_at = datetime.utcnow() + timedelta(seconds=ttl)

    raw_token, token_hash = generate_opaque_token(32)

    config = {
        "user_ref":      body.get("user_ref"),
        "context_token": body.get("context_token"),
        "locale":        body.get("locale", "en"),
        "theme":         body.get("theme", "light"),
        "_widget":       True,
    }
    encrypted = encrypt_field(json.dumps(config))

    session = ContextSession(
        client_id           = ctx.client.id,
        token_hash          = token_hash,
        pre_filled_data_enc = encrypted,
        project_id          = uuid.UUID(body["project_id"]) if body.get("project_id") else None,
        org_id              = uuid.UUID(body["org_id"])      if body.get("org_id")     else None,
        expires_at          = expires_at,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    log.info("integration.widget_session_created", client_id=str(ctx.client.id))

    return {
        "embed_token":  raw_token,
        "session_id":   str(session.id),
        "expires_at":   expires_at.isoformat(),
        "ttl_seconds":  ttl,
        "embed_url":    f"{settings.RIVIWA_WIDGET_BASE_URL}/embed?token={raw_token}",
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

    Checks Origin header against the client's allowed_origins list.
    Returns CORS headers and widget configuration.
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
        "scopes":        client.allowed_scopes,
        "require_auth":  "feedback:write" in client.allowed_scopes,
    }

    # If a session token was provided, attach context
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
                config["pre_fill"] = json.loads(decrypt_field(sess.pre_filled_data_enc))
            except Exception:
                pass


    headers = {
        "Access-Control-Allow-Origin": origin or "*",
        "Access-Control-Allow-Credentials": "true",
        "Vary": "Origin",
    }
    return JSONResponse(content=config, headers=headers)


# ── GET /integration/widget/snippet — JS tag snippet for copy-paste ──────────

@router.get("/snippet")
async def get_embed_snippet(
    client_id: str,
    db: AsyncSession = Depends(get_async_session),
    ctx: AuthContext = IntegrationAuthDep,
) -> dict:
    """
    Returns the copy-paste JS snippet that partners include on their website.
    Similar to Google Tag / HubSpot tracking snippet.
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

    base = settings.RIVIWA_WIDGET_BASE_URL
    # Double-brace JS curly braces to escape f-string interpolation
    snippet = (
        "<!-- Riviwa Feedback Widget -->\n"
        "<script>\n"
        "  (function(r,i,v,i2,w,a){{r['RiviwaObject']=w;r[w]=r[w]||function(){{}}\n"
        "  ;(r[w].q=r[w].q||[]).push(arguments)}},r[w].l=1*new Date();a=i.createElement(v),\n"
        "  m=i.getElementsByTagName(v)[0];a.async=1;a.src=i2;m.parentNode.insertBefore(a,m)\n"
        f"  }})(window,document,'script','{base}/widget.js','riviwa');\n"
        f"  riviwa('init', '{client_id}');\n"
        "  riviwa('track', 'page_view');\n"
        "</script>\n"
        "<!-- End Riviwa Feedback Widget -->"
    )

    return {
        "client_id": client_id,
        "snippet":   snippet,
        "widget_js": f"{base}/widget.js",
        "docs_url":  "https://docs.riviwa.com/integration/widget",
    }

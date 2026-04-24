"""
api/v1/feedback_bridge.py — Feedback submission bridge.

Partners submit feedback (grievances, suggestions, applauses, inquiries)
through this endpoint. Riviwa:
  1. Validates the client's org scope
  2. Optionally consumes a context session to merge pre-filled data
  3. Optionally fetches additional context from the partner's data endpoint
  4. Forwards the enriched payload to feedback_service as an internal call
  5. Fires a webhook to the partner with the created feedback reference

This means a mobile banking app or website can submit feedback on behalf of
their customer without the customer ever leaving the partner's interface.

Auth: Bearer token or API key (standard integration auth).
Required scope: feedback:write
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Optional

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import IntegrationAuthDep, AuthContext
from core.config import settings
from core.security import decrypt_field, hash_code
from db.session import get_async_session
from models.integration import ContextSession
from services.data_bridge import fetch_external_context
from services.webhook_worker import enqueue_webhook

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/integration/feedback", tags=["Integration — Feedback Bridge"])


# ── POST /integration/feedback — Submit feedback on behalf of a user ──────────

@router.post("", status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    ctx: AuthContext = IntegrationAuthDep,
) -> dict:
    """
    Submit feedback through a partner integration, scoped to the client's org.

    The org_id is always derived from the client registration — partners cannot
    submit feedback for a different organisation.

    Body fields:
      feedback_type   — "GRIEVANCE" | "SUGGESTION" | "APPLAUSE" | "INQUIRY" (required)
      title           — short description (required)
      description     — full description (optional)
      category_id     — Riviwa feedback category UUID (optional)
      department_id   — Riviwa department UUID (optional)
      project_id      — Riviwa project UUID; defaults to client's default project (optional)
      priority        — "LOW" | "MEDIUM" | "HIGH" (default: MEDIUM)
      channel         — submission channel hint, e.g. "MOBILE_APP" | "WEB_WIDGET" | "CHATBOT"

      # User identity (at least one required unless context_token provided)
      phone           — submitter's phone number
      name            — submitter's full name
      email           — submitter's email
      account_ref     — partner's internal account reference

      # Context session (pre-filled data from a prior POST /integration/context)
      context_token   — if provided, merges pre-fill data (phone/name/etc.)
                        and consumes the session

      # External data bridge (pulls context from partner's configured endpoint)
      enrich_from_endpoint — bool (default false); triggers a call to
                             client.data_endpoint_url if configured

      # Metadata
      source_ref      — partner's internal reference for this submission
      metadata        — freeform dict passed through as-is
    """
    ctx.require_scope("feedback:write")
    org_id = ctx.validate_org(
        uuid.UUID(body["org_id"]) if body.get("org_id") else None
    )

    feedback_type = body.get("feedback_type", "GRIEVANCE").upper()
    if feedback_type not in ("GRIEVANCE", "SUGGESTION", "APPLAUSE", "INQUIRY"):
        raise HTTPException(400, {"error": "INVALID_FEEDBACK_TYPE",
                                  "allowed": ["GRIEVANCE", "SUGGESTION", "APPLAUSE", "INQUIRY"]})

    title = body.get("title", "").strip()
    if not title:
        raise HTTPException(400, {"error": "TITLE_REQUIRED"})

    # ── 1. Merge context session if provided ──────────────────────────────────
    pre_fill: dict = {}
    if body.get("context_token"):
        token_hash = hash_code(body["context_token"])
        from sqlalchemy import select
        result = await db.execute(
            select(ContextSession).where(
                ContextSession.token_hash  == token_hash,
                ContextSession.consumed_at.is_(None),
            )
        )
        sess = result.scalars().first()
        if sess:
            if sess.expires_at < datetime.utcnow():
                raise HTTPException(410, {"error": "CONTEXT_SESSION_EXPIRED"})
            # Validate session belongs to same org
            if sess.org_id and sess.org_id != org_id:
                raise HTTPException(403, {"error": "CONTEXT_SESSION_ORG_MISMATCH"})
            try:
                pre_fill = json.loads(decrypt_field(sess.pre_filled_data_enc))
            except Exception:
                pass
            # Consume session
            sess.consumed_at = datetime.utcnow()
            # Inherit project_id from session if not in body
            if sess.project_id and not body.get("project_id"):
                body["project_id"] = str(sess.project_id)
        else:
            log.warning("integration.context_token_not_found")

    # ── 2. Optional data bridge enrichment ───────────────────────────────────
    if body.get("enrich_from_endpoint") and ctx.client.data_endpoint_url:
        lookup_key  = body.get("phone") or pre_fill.get("phone") or body.get("account_ref") or pre_fill.get("account_ref")
        lookup_type = "phone" if (body.get("phone") or pre_fill.get("phone")) else "account_ref"
        if lookup_key:
            enriched = await fetch_external_context(ctx.client, lookup_key, lookup_type)
            if enriched:
                pre_fill.update(enriched)

    # ── 3. Build final user identity ─────────────────────────────────────────
    phone      = body.get("phone")      or pre_fill.get("phone")
    name       = body.get("name")       or pre_fill.get("name")
    email      = body.get("email")      or pre_fill.get("email")
    account_ref = body.get("account_ref") or pre_fill.get("account_ref")

    if not any([phone, name, email, account_ref]):
        raise HTTPException(400, {"error": "SUBMITTER_IDENTITY_REQUIRED",
                                  "message": "Provide at least one of: phone, name, email, account_ref — or a valid context_token"})

    # ── 4. Forward to feedback_service ───────────────────────────────────────
    feedback_payload = {
        "feedback_type":  feedback_type,
        "title":          title,
        "description":    body.get("description", ""),
        "category_id":    body.get("category_id") or pre_fill.get("category_id"),
        "department_id":  body.get("department_id") or pre_fill.get("department_id"),
        "project_id":     body.get("project_id") or pre_fill.get("project_id") or str(pre_fill.get("project_id", "")),
        "priority":       body.get("priority", "MEDIUM").upper(),
        "channel":        body.get("channel", "API"),
        "org_id":         str(org_id),
        # Submitter identity
        "phone":          phone,
        "name":           name,
        "email":          email,
        "account_ref":    account_ref,
        # Integration metadata
        "integration_client_id": ctx.client.client_id,
        "source_ref":    body.get("source_ref"),
        "metadata":      body.get("metadata"),
    }
    # Strip None values
    feedback_payload = {k: v for k, v in feedback_payload.items() if v is not None and v != ""}

    feedback_result = await _forward_to_feedback_service(feedback_payload)

    # ── 5. Commit context session consumption ────────────────────────────────
    await db.commit()

    # ── 6. Enqueue webhook for partner ───────────────────────────────────────
    webhook_payload = {
        "event":       "feedback.submitted",
        "feedback_id": feedback_result.get("id"),
        "reference":   feedback_result.get("reference"),
        "org_id":      str(org_id),
        "feedback_type": feedback_type,
        "source_ref":  body.get("source_ref"),
        "submitted_at": datetime.utcnow().isoformat(),
    }
    delivery = await enqueue_webhook(db, ctx.client.id, "feedback.submitted", webhook_payload)
    if delivery:
        await db.commit()

    log.info("integration.feedback_submitted",
             client_id=str(ctx.client.id),
             org_id=str(org_id),
             feedback_id=feedback_result.get("id"),
             feedback_type=feedback_type)

    return {
        "feedback_id":   feedback_result.get("id"),
        "reference":     feedback_result.get("reference"),
        "org_id":        str(org_id),
        "feedback_type": feedback_type,
        "status":        feedback_result.get("status", "SUBMITTED"),
        "submitted_at":  datetime.utcnow().isoformat(),
        "webhook_queued": delivery is not None,
    }


# ── GET /integration/feedback/{feedback_id} — Check submission status ─────────

@router.get("/{feedback_id}")
async def get_feedback_status(
    feedback_id: uuid.UUID,
    ctx: AuthContext = IntegrationAuthDep,
) -> dict:
    """
    Check the status of a previously submitted feedback item.
    Validates the feedback belongs to the client's bound org.
    """
    ctx.require_scope("feedback:read")
    org_id = ctx.require_org()

    try:
        async with httpx.AsyncClient(timeout=10.0) as http:
            resp = await http.get(
                f"{settings.FEEDBACK_SERVICE_URL}/api/v1/feedback/{feedback_id}",
                headers={"X-Service-Key": settings.INTERNAL_SERVICE_KEY},
            )
        if resp.status_code == 404:
            raise HTTPException(404, {"error": "FEEDBACK_NOT_FOUND"})
        if resp.status_code != 200:
            raise HTTPException(502, {"error": "FEEDBACK_SERVICE_ERROR"})

        data = resp.json()
        # Org scope check
        if str(data.get("org_id")) != str(org_id):
            raise HTTPException(403, {"error": "ORG_MISMATCH"})

        return {
            "feedback_id":   str(feedback_id),
            "reference":     data.get("reference"),
            "org_id":        str(org_id),
            "feedback_type": data.get("feedback_type"),
            "status":        data.get("status"),
            "title":         data.get("title"),
            "priority":      data.get("priority"),
            "created_at":    data.get("created_at"),
            "updated_at":    data.get("updated_at"),
        }
    except HTTPException:
        raise
    except Exception as exc:
        log.error("integration.feedback_status_error", error=str(exc))
        raise HTTPException(502, {"error": "FEEDBACK_SERVICE_UNAVAILABLE"})


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _forward_to_feedback_service(payload: dict) -> dict:
    """POST to feedback_service internal endpoint."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as http:
            resp = await http.post(
                f"{settings.FEEDBACK_SERVICE_URL}/api/v1/feedback",
                json=payload,
                headers={
                    "X-Service-Key":  settings.INTERNAL_SERVICE_KEY,
                    "X-Integration":  "true",
                    "Content-Type":   "application/json",
                },
            )
        if resp.status_code in (200, 201):
            return resp.json()

        log.error("integration.feedback_forward_failed",
                  status=resp.status_code, body=resp.text[:500])
        raise HTTPException(
            status_code=502,
            detail={"error": "FEEDBACK_SERVICE_ERROR",
                    "message": f"feedback_service returned {resp.status_code}"},
        )
    except HTTPException:
        raise
    except Exception as exc:
        log.error("integration.feedback_forward_exception", error=str(exc))
        raise HTTPException(
            status_code=503,
            detail={"error": "FEEDBACK_SERVICE_UNAVAILABLE",
                    "message": "Could not reach feedback_service"},
        )

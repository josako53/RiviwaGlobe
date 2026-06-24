"""api/v1/admin.py — Staff-only AI management endpoints."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status
from core.dependencies import AdminOrSvcDep, DbDep, StaffDep, TokenClaims
from models.conversation import ConversationStatus
from repositories.conversation_repo import ConversationRepository

_PLATFORM_ADMINS = {"super_admin", "admin"}


def _caller_org_id(claims: TokenClaims) -> Optional[uuid.UUID]:
    """Return org_id for scoping, or None if the caller is a platform admin (sees all)."""
    if claims.platform_role in _PLATFORM_ADMINS:
        return None
    return claims.org_id


def _check_org_ownership(conv_org_id: Optional[uuid.UUID], caller_org_id: Optional[uuid.UUID]) -> None:
    """Raise 403 if caller_org_id is set and does not match the conversation's org."""
    if caller_org_id is not None and conv_org_id != caller_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this conversation.",
        )

router = APIRouter(prefix="/ai/admin", tags=["AI Admin"])


@router.get("/conversations", summary="List all AI conversations (staff only)")
async def list_conversations(
    db: DbDep, claims: StaffDep,
    status_: Optional[str] = Query(default=None, alias="status"),
    channel: Optional[str] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    repo  = ConversationRepository(db)
    items = await repo.list(
        status=status_,
        channel=channel,
        org_id=_caller_org_id(claims),
        skip=skip,
        limit=limit,
    )
    return {
        "items": [
            {
                "conversation_id": str(c.id),
                "channel":         c.channel.value,
                "status":          c.status.value,
                "stage":           c.stage.value,
                "language":        c.language,
                "turn_count":      c.turn_count,
                "is_registered":   c.is_registered,
                "phone_number":    c.phone_number,
                "project_name":    c.project_name,
                "is_urgent":       c.is_urgent,
                "started_at":      c.started_at.isoformat(),
                "last_active_at":  c.last_active_at.isoformat(),
            }
            for c in items
        ],
        "count": len(items),
    }


@router.get("/conversations/{conversation_id}", summary="Conversation detail with full transcript")
async def get_conversation_admin(conversation_id: uuid.UUID, db: DbDep, claims: StaffDep) -> dict:
    repo = ConversationRepository(db)
    conv = await repo.get_or_404(conversation_id)
    _check_org_ownership(conv.org_id, _caller_org_id(claims))
    extracted = conv.get_extracted()
    return {
        "conversation_id": str(conv.id),
        "channel":         conv.channel.value,
        "status":          conv.status.value,
        "stage":           conv.stage.value,
        "language":        conv.language,
        "turn_count":      conv.turn_count,
        "confidence":      float(extracted.get("confidence", 0.0)),
        "is_registered":   conv.is_registered,
        "submitter_name":  conv.submitter_name,
        "phone_number":    conv.phone_number,
        "whatsapp_id":     conv.whatsapp_id,
        "user_id":         str(conv.user_id) if conv.user_id else None,
        "project_id":      str(conv.project_id) if conv.project_id else None,
        "project_name":    conv.project_name,
        "extracted_data":  extracted,
        "submitted_feedback": conv.get_submitted(),
        "transcript":      conv.get_turns(),
        "is_urgent":       conv.is_urgent,
        "incharge_name":   conv.incharge_name,
        "incharge_phone":  conv.incharge_phone,
        "started_at":      conv.started_at.isoformat(),
        "last_active_at":  conv.last_active_at.isoformat(),
        "completed_at":    conv.completed_at.isoformat() if conv.completed_at else None,
    }


@router.post(
    "/conversations/{conversation_id}/force-submit",
    summary="Force-submit feedback from current extracted data (staff override)",
    status_code=status.HTTP_200_OK,
)
async def force_submit(conversation_id: uuid.UUID, db: DbDep, claims: StaffDep) -> dict:
    from services.conversation_service import ConversationService
    svc  = ConversationService(db=db)
    conv = await svc.conv_repo.get_or_404(conversation_id)
    _check_org_ownership(conv.org_id, _caller_org_id(claims))
    submitted, results = await svc._submit_feedback(conv)
    if submitted:
        from models.conversation import ConversationStatus, ConversationStage
        from datetime import datetime, timezone
        conv.status       = ConversationStatus.SUBMITTED
        conv.stage        = ConversationStage.DONE
        conv.completed_at = datetime.now(timezone.utc)
        await svc.conv_repo.save(conv)
    return {"submitted": submitted, "results": results}


@router.post(
    "/reindex-projects",
    summary="Re-index all projects from DB into Qdrant (staff only)",
    status_code=status.HTTP_200_OK,
)
async def reindex_projects(db: DbDep, _: StaffDep) -> dict:
    """
    Reads all projects from ai_project_kb and re-indexes them into Qdrant
    with the current enriched text. Run this after deploying richer indexing logic.
    """
    from sqlmodel import select
    from models.conversation import ProjectKnowledgeBase
    from services.rag_service import get_rag

    rows = (await db.execute(select(ProjectKnowledgeBase))).scalars().all()
    rag = get_rag()
    indexed = 0
    failed = 0
    for kb in rows:
        searchable = kb.get_searchable_text()
        payload = {
            "name":               kb.name,
            "code":               kb.code or "",
            "sector":             kb.sector or "",
            "category":           kb.category or "",
            "description":        kb.description or "",
            "objectives":         (kb.objectives or "")[:300],
            "location_description": kb.location_description or "",
            "funding_source":     kb.funding_source or "",
            "region":             kb.region or "",
            "primary_lga":        kb.primary_lga or "",
            "org_display_name":   kb.org_display_name or "",
            "organisation_id":    str(kb.organisation_id),
            "branch_id":          str(kb.branch_id) if kb.branch_id else "",
            "status":             kb.status,
        }
        ok = rag.index_project(kb.project_id, searchable, payload)
        if ok:
            kb.vector_indexed = True
            db.add(kb)
            indexed += 1
        else:
            failed += 1
    await db.commit()
    return {"indexed": indexed, "failed": failed, "total": len(rows)}


@router.post(
    "/index-vault",
    summary="Index Obsidian vault .md files into Qdrant knowledge base (staff only)",
    status_code=status.HTTP_200_OK,
)
async def index_vault(_: StaffDep) -> dict:
    """
    Scans OBSIDIAN_VAULT_PATH for .md files, chunks them, embeds and upserts to
    Qdrant 'riviwa_knowledge' collection. Safe to run multiple times (upsert).
    """
    from services.obsidian_rag_service import get_obsidian_rag
    chunks = get_obsidian_rag().index_vault()
    return {"chunks_indexed": chunks}


@router.post(
    "/reindex/{entity_type}",
    summary="Bulk-reindex entity collection into Qdrant (staff only)",
    status_code=status.HTTP_200_OK,
)
async def reindex_entities(entity_type: str, _: AdminOrSvcDep) -> dict:
    """
    Pulls all entities of the given type from the source service and re-indexes
    them into the appropriate Qdrant collection.

    entity_type: orgs | branches | departments | services | staff
    """
    import httpx as _httpx
    from core.config import settings as _cfg
    from services.rag_service import get_rag as _get_rag

    _INTERNAL = {
        "X-Service-Key": _cfg.INTERNAL_SERVICE_KEY,
        "X-Service-Name": "ai_service",
    }
    rag = _get_rag()
    indexed = 0
    failed  = 0

    async def _fetch(url: str, params: dict | None = None) -> list:
        async with _httpx.AsyncClient(timeout=30) as c:
            r = await c.get(url, params=params or {}, headers=_INTERNAL)
            if r.status_code != 200:
                return []
            data = r.json()
            return data.get("items", data) if isinstance(data, dict) else data

    if entity_type == "orgs":
        items = await _fetch(f"{_cfg.AUTH_SERVICE_URL}/api/v1/internal/organisations", {"limit": 500})
        for item in items:
            eid = item.get("id")
            if eid and rag.index_org(str(eid), item):
                indexed += 1
            else:
                failed += 1

    elif entity_type == "branches":
        items = await _fetch(f"{_cfg.AUTH_SERVICE_URL}/api/v1/internal/branches", {"limit": 1000})
        for item in items:
            eid = item.get("id")
            if eid and rag.index_branch(str(eid), item):
                indexed += 1
            else:
                failed += 1

    elif entity_type == "departments":
        items = await _fetch(f"{_cfg.AUTH_SERVICE_URL}/api/v1/internal/departments", {"limit": 1000})
        for item in items:
            eid = item.get("id")
            if eid and rag.index_department(str(eid), item):
                indexed += 1
            else:
                failed += 1

    elif entity_type == "services":
        items = await _fetch(f"{_cfg.AUTH_SERVICE_URL}/api/v1/internal/services", {"limit": 1000})
        for item in items:
            eid = item.get("id")
            if eid and rag.index_service(str(eid), item):
                indexed += 1
            else:
                failed += 1

    elif entity_type == "staff":
        items = await _fetch(f"{_cfg.STAFF_SERVICE_URL}/api/v1/internal/staff", {"limit": 1000})
        for item in items:
            eid = item.get("id")
            if eid and rag.index_staff(str(eid), item):
                indexed += 1
            else:
                failed += 1

    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown entity_type '{entity_type}'. Valid: orgs, branches, departments, services, staff",
        )

    return {"entity_type": entity_type, "indexed": indexed, "failed": failed, "total": indexed + failed}


@router.patch(
    "/conversations/{conversation_id}",
    summary="Update conversation metadata (staff only)",
    status_code=status.HTTP_200_OK,
)
async def update_conversation(
    conversation_id: uuid.UUID,
    body: dict,
    db: DbDep,
    claims: StaffDep,
) -> dict:
    """
    Update mutable metadata on a conversation.

    Patchable fields:
      is_urgent       — bool
      incharge_name   — str (person to escalate to)
      incharge_phone  — str
      status          — active | abandoned | archived
      language        — override detected language (e.g. "en" → "sw")
    """
    repo = ConversationRepository(db)
    conv = await repo.get_or_404(conversation_id)
    _check_org_ownership(conv.org_id, _caller_org_id(claims))

    allowed = {"is_urgent", "incharge_name", "incharge_phone", "language"}
    for field in allowed:
        if field in body:
            setattr(conv, field, body[field])

    if "status" in body:
        try:
            new_status = ConversationStatus(body["status"])
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid status '{body['status']}'. Valid values: {[s.value for s in ConversationStatus]}",
            )
        conv.status = new_status

    conv.last_active_at = datetime.now(timezone.utc)
    await repo.save(conv)

    return {
        "conversation_id": str(conv.id),
        "status":          conv.status.value,
        "language":        conv.language,
        "is_urgent":       conv.is_urgent,
        "incharge_name":   conv.incharge_name,
        "incharge_phone":  conv.incharge_phone,
        "updated_at":      conv.last_active_at.isoformat(),
    }


@router.delete(
    "/conversations/{conversation_id}",
    summary="Archive a conversation (staff only)",
    status_code=status.HTTP_200_OK,
)
async def archive_conversation(
    conversation_id: uuid.UUID,
    db: DbDep,
    claims: StaffDep,
) -> dict:
    """
    Soft-deletes a conversation by setting status to ARCHIVED.
    Archived conversations are excluded from Consumer-facing GET endpoints
    but remain in the database for audit purposes.

    To permanently delete, use the database directly (no API exists intentionally).
    """
    repo = ConversationRepository(db)
    conv = await repo.get_or_404(conversation_id)
    _check_org_ownership(conv.org_id, _caller_org_id(claims))

    if conv.status == ConversationStatus.ARCHIVED:
        return {"message": "Conversation already archived.", "conversation_id": str(conv.id)}

    conv.status         = ConversationStatus.ARCHIVED
    conv.completed_at   = conv.completed_at or datetime.now(timezone.utc)
    conv.last_active_at = datetime.now(timezone.utc)
    await repo.save(conv)

    return {
        "message":         "Conversation archived.",
        "conversation_id": str(conv.id),
        "archived_at":     conv.last_active_at.isoformat(),
    }

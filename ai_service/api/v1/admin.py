"""api/v1/admin.py — Staff-only AI management endpoints."""
from __future__ import annotations
import uuid
from typing import Optional
from fastapi import APIRouter, Query, status
from core.dependencies import DbDep, StaffDep
from repositories.conversation_repo import ConversationRepository

router = APIRouter(prefix="/ai/admin", tags=["AI Admin"])


@router.get("/conversations", summary="List all AI conversations (staff only)")
async def list_conversations(
    db: DbDep, _: StaffDep,
    status_: Optional[str] = Query(default=None, alias="status"),
    channel: Optional[str] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    repo  = ConversationRepository(db)
    items = await repo.list(status=status_, channel=channel, skip=skip, limit=limit)
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
async def get_conversation_admin(conversation_id: uuid.UUID, db: DbDep, _: StaffDep) -> dict:
    repo = ConversationRepository(db)
    conv = await repo.get_or_404(conversation_id)
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
async def force_submit(conversation_id: uuid.UUID, db: DbDep, _: StaffDep) -> dict:
    from services.conversation_service import ConversationService
    svc  = ConversationService(db=db)
    conv = await svc.conv_repo.get_or_404(conversation_id)
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

"""
api/v1/internal.py — Internal service-to-service endpoints for ai_service.

These endpoints require X-Service-Key header only (no JWT).
Used by feedback_service to classify Consumer feedback before submission.
"""
from __future__ import annotations
from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from core.dependencies import DbDep

router = APIRouter(prefix="/ai/internal", tags=["AI Internal"])


@router.post(
    "/classify",
    status_code=status.HTTP_200_OK,
    summary="Classify feedback: auto-detect project_id and category (internal only)",
    include_in_schema=False,
)
async def classify_feedback(request: Request) -> dict:
    """
    Called by feedback_service during Consumer submission when project_id or category is missing.

    Input JSON:
      {
        "feedback_type": "grievance|suggestion|applause",
        "description": "...",
        "issue_location_description": "...",   # optional
        "issue_lga":  "...",                    # optional
        "issue_ward": "...",                    # optional
        "issue_region": "..."                   # optional
      }

    Returns:
      {
        "project_id": "<uuid or null>",
        "project_name": "...",
        "category_slug": "...",
        "category_def_id": "<uuid or null>",
        "confidence": 0.85,
        "classified": true
      }
    """
    from core.config import settings
    from services.classification_service import ClassificationService

    # Validate internal service key
    service_key = request.headers.get("X-Service-Key", "")
    if service_key != settings.INTERNAL_SERVICE_KEY:
        return JSONResponse(
            status_code=403,
            content={"error": "FORBIDDEN", "message": "Invalid service key."},
        )

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content={"error": "BAD_REQUEST", "message": "Invalid JSON body."},
        )

    svc = ClassificationService()
    result = await svc.classify_new_feedback(
        feedback_type              = body.get("feedback_type", "grievance"),
        description                = body.get("description", ""),
        issue_location_description = body.get("issue_location_description"),
        issue_lga                  = body.get("issue_lga"),
        issue_ward                 = body.get("issue_ward"),
        issue_region               = body.get("issue_region"),
        project_id_hint            = body.get("project_id"),
    )
    return result


@router.post(
    "/candidate-projects",
    status_code=status.HTTP_200_OK,
    summary="Return top candidate projects for a Consumer's location (internal only)",
    include_in_schema=False,
)
async def candidate_projects(request: Request, db: DbDep) -> dict:
    """
    Called by feedback_service when AI classification returns no confident project match.
    Returns the top N projects ranked by semantic similarity to the Consumer's description + location.
    The frontend uses this list to show a project picker.

    Input JSON:
      {
        "description": "...",
        "issue_lga": "...",
        "issue_ward": "...",
        "issue_location_description": "...",
        "top_k": 5
      }

    Returns:
      {
        "projects": [
          {"project_id": "...", "name": "...", "region": "...", "lga": "...", "score": 0.72},
          ...
        ]
      }
    """
    from core.config import settings
    from services.rag_service import get_rag

    service_key = request.headers.get("X-Service-Key", "")
    if service_key != settings.INTERNAL_SERVICE_KEY:
        return JSONResponse(
            status_code=403,
            content={"error": "FORBIDDEN", "message": "Invalid service key."},
        )

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content={"error": "BAD_REQUEST", "message": "Invalid JSON body."},
        )

    top_k = min(int(body.get("top_k", 5)), 10)
    query_parts = []
    for key in ("issue_location_description", "issue_lga", "issue_ward", "description"):
        val = body.get(key, "")
        if val:
            query_parts.append(str(val)[:150])

    if not query_parts:
        return {"projects": []}

    results = get_rag().search_projects(
        " ".join(query_parts),
        top_k=top_k,
        score_threshold=0.0,   # return all results, sorted by score
    )

    if results:
        projects = [
            {
                "project_id": pid,
                "name":       payload.get("name", ""),
                "region":     payload.get("region", ""),
                "lga":        payload.get("primary_lga", ""),
                "score":      round(score, 3),
            }
            for pid, score, payload in results
        ]
        return {"projects": projects}

    # Qdrant is empty (no projects indexed yet) — fall back to DB
    from sqlalchemy import select
    from models.conversation import ProjectKnowledgeBase
    try:
        rows = (await db.execute(
            select(ProjectKnowledgeBase)
            .where(ProjectKnowledgeBase.status == "active")
            .order_by(ProjectKnowledgeBase.name)
            .limit(top_k)
        )).scalars().all()
        projects = [
            {
                "project_id": str(row.project_id),
                "name":       row.name,
                "region":     row.region or "",
                "lga":        row.primary_lga or "",
                "score":      0.0,
            }
            for row in rows
        ]
    except Exception as exc:
        import structlog
        structlog.get_logger(__name__).error("candidate_projects.db_fallback_failed", error=str(exc))
        projects = []

    return {"projects": projects}

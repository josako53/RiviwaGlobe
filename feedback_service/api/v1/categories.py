"""api/v1/categories.py — HTTP orchestration only"""
from __future__ import annotations
import uuid
from typing import Any, Dict, Literal, Optional
from fastapi import APIRouter, Query, status
from core.dependencies import DbDep, StaffDep
from services.category_service import CategoryService
from api.v1.serialisers import category_out

router = APIRouter(tags=["Categories"])
def _svc(db): return CategoryService(db=db)

def _cat(c):
    if c is None: return None
    return category_out(c)

@router.post("/categories", status_code=status.HTTP_201_CREATED, summary="Create a feedback category")
async def create_category(body: Dict[str, Any], db: DbDep, token: StaffDep) -> dict:
    return _cat(await _svc(db).create(body, created_by=token.sub))

@router.get("/categories", summary="List feedback categories")
async def list_categories(
    db: DbDep, _: StaffDep,
    project_id: Optional[uuid.UUID] = Query(default=None),
    feedback_type: Optional[str] = Query(default=None),
    source: Optional[str] = Query(default=None),
    status_: Optional[str] = Query(default=None, alias="status"),
    include_global: bool = Query(default=True),
    skip: int = Query(default=0, ge=0), limit: int = Query(default=100, ge=1, le=500),
) -> dict:
    items = await _svc(db).list(project_id=project_id, feedback_type=feedback_type,
        source=source, status=status_, include_global=include_global, skip=skip, limit=limit)
    return {"items": [_cat(c) for c in items], "count": len(items)}

@router.get("/categories/summary", summary="All category counts for a project — for dashboard overview")
async def categories_summary(
    db: DbDep, _: StaffDep,
    project_id: uuid.UUID = Query(...),
    feedback_type: Optional[str] = Query(default=None),
    from_date: Optional[str] = Query(default=None),
    to_date: Optional[str] = Query(default=None),
) -> dict:
    result = await _svc(db).summary(project_id, feedback_type=feedback_type,
                                    from_date=from_date, to_date=to_date)
    result["categories"] = [
        {**r, "category": _cat(r["category"])} for r in result["categories"]
    ]
    return result

@router.get("/categories/{category_id}", summary="Category detail")
async def get_category(category_id: uuid.UUID, db: DbDep, _: StaffDep) -> dict:
    return _cat(await _svc(db).get_or_404(category_id))

@router.patch("/categories/{category_id}", summary="Update category")
async def update_category(category_id: uuid.UUID, body: Dict[str, Any], db: DbDep, _: StaffDep) -> dict:
    return _cat(await _svc(db).update(category_id, body))

@router.get("/categories/{category_id}/rate", summary="Feedback rate for a category — real-time and by period")
async def category_rate(
    category_id: uuid.UUID, db: DbDep, _: StaffDep,
    project_id: Optional[uuid.UUID] = Query(default=None),
    stage_id: Optional[uuid.UUID] = Query(default=None),
    period: str = Query(default="week"),
    from_date: Optional[str] = Query(default=None),
    to_date: Optional[str] = Query(default=None),
    feedback_type: Optional[str] = Query(default=None),
    status_: Optional[str] = Query(default=None, alias="status"),
    open_only: bool = Query(default=False),
    priority: Optional[str] = Query(default=None),
    current_level: Optional[str] = Query(default=None),
    lga: Optional[str] = Query(default=None),
    ward: Optional[str] = Query(default=None),
    is_anonymous: Optional[bool] = Query(default=None),
    submitted_by_stakeholder_id: Optional[uuid.UUID] = Query(default=None),
    assigned_committee_id: Optional[uuid.UUID] = Query(default=None),
    assigned_to_user_id: Optional[uuid.UUID] = Query(default=None),
) -> dict:
    result = await _svc(db).rate(
        category_id, period=period, project_id=project_id, stage_id=stage_id,
        from_date=from_date, to_date=to_date, feedback_type=feedback_type,
        status=status_, open_only=open_only, priority=priority,
        current_level=current_level, lga=lga, ward=ward, is_anonymous=is_anonymous,
        submitted_by_stakeholder_id=submitted_by_stakeholder_id,
        assigned_committee_id=assigned_committee_id, assigned_to_user_id=assigned_to_user_id,
    )
    result["category"] = _cat(result["category"])
    return result

@router.post("/categories/{category_id}/approve", summary="Approve an ML-suggested category")
async def approve_category(category_id: uuid.UUID, body: Dict[str, Any], db: DbDep, token: StaffDep) -> dict:
    return _cat(await _svc(db).approve(category_id, body, by=token.sub))

@router.post("/categories/{category_id}/reject", summary="Reject an ML-suggested category")
async def reject_category(category_id: uuid.UUID, body: Dict[str, Any], db: DbDep, token: StaffDep) -> dict:
    return _cat(await _svc(db).reject(category_id, body, by=token.sub))

@router.post("/categories/{category_id}/deactivate", summary="Deactivate a category")
async def deactivate_category(category_id: uuid.UUID, body: Dict[str, Any], db: DbDep, _: StaffDep) -> dict:
    return _cat(await _svc(db).deactivate(category_id, body))

@router.post("/categories/{category_id}/merge", summary="Merge into another category")
async def merge_category(category_id: uuid.UUID, body: Dict[str, Any], db: DbDep, _: StaffDep) -> dict:
    return _cat(await _svc(db).merge(category_id, body))

@router.post("/feedback/{feedback_id}/classify", status_code=status.HTTP_200_OK, summary="Run ML classification to assign or suggest a category")
async def classify_feedback(feedback_id: uuid.UUID, body: Dict[str, Any], db: DbDep, _: StaffDep) -> dict:
    result = await _svc(db).classify(feedback_id, body)
    result["category"] = _cat(result["category"])
    return result

@router.patch("/feedback/{feedback_id}/recategorise", status_code=status.HTTP_200_OK, summary="Manually reassign category to a feedback submission")
async def recategorise_feedback(feedback_id: uuid.UUID, body: Dict[str, Any], db: DbDep, _: StaffDep) -> dict:
    result = await _svc(db).recategorise(feedback_id, body)
    result["category"] = _cat(result["category"])
    return result

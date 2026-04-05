# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  notification_service  |  Port: 8060  |  DB: notification_db (5437)
# FILE     :  api/v1/templates.py
# ───────────────────────────────────────────────────────────────────────────
"""api/v1/templates.py — Template CRUD (admin operations)."""
from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status

from core.dependencies import DbDep, ServiceKeyDep
from repositories.notification_repository import NotificationRepository
from schemas.notification import TemplateRequest, TemplateResponse

router = APIRouter(prefix="/templates", tags=["Templates (Admin)"])

_svc_guard = ServiceKeyDep  # all template management requires internal service key


@router.get(
    "",
    response_model=List[TemplateResponse],
    summary="List notification templates",
    dependencies=[ServiceKeyDep],
)
async def list_templates(
    db:                DbDep,
    notification_type: Optional[str] = Query(default=None),
    channel:           Optional[str] = Query(default=None),
    language:          Optional[str] = Query(default=None),
) -> List[TemplateResponse]:
    repo  = NotificationRepository(db)
    tmpls = await repo.list_templates(notification_type, channel, language)
    return [TemplateResponse.model_validate(t.__dict__) for t in tmpls]


@router.put(
    "",
    response_model=TemplateResponse,
    status_code=status.HTTP_200_OK,
    summary="Create or update a notification template",
    description=(
        "Upsert a template by (notification_type, channel, language). "
        "Use Jinja2 syntax for variables: {{ feedback_ref }}, {{ project_name }}. "
        "Email body_template supports HTML."
    ),
    dependencies=[ServiceKeyDep],
)
async def upsert_template(body: TemplateRequest, db: DbDep) -> TemplateResponse:
    repo  = NotificationRepository(db)
    tmpl  = await repo.upsert_template(body.model_dump(exclude_none=True))
    await db.commit()
    await db.refresh(tmpl)
    return TemplateResponse.model_validate(tmpl.__dict__)


@router.delete(
    "/{template_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a template",
    dependencies=[ServiceKeyDep],
)
async def delete_template(template_id: uuid.UUID, db: DbDep) -> dict:
    repo    = NotificationRepository(db)
    deleted = await repo.delete_template(template_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Template not found.")
    await db.commit()
    return {"message": "Template deleted."}

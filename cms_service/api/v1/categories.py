"""api/v1/categories.py — CMS category CRUD."""
from __future__ import annotations
import re
import uuid
from typing import Optional
from fastapi import APIRouter, Query, status
from sqlalchemy import select

from core.dependencies import AuthDep, DbDep, StaffDep
from core.exceptions import ConflictError, NotFoundError
from models.post import OrgPostCategory
from schemas.post import CategoryCreate, CategoryOut, CategoryUpdate

router = APIRouter(prefix="/cms/categories", tags=["CMS — Categories"])


def _slugify(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    return re.sub(r"[\s_-]+", "-", s).strip("-")


async def _get_category_or_404(cat_id: uuid.UUID, db: DbDep) -> OrgPostCategory:
    cat = (await db.execute(
        select(OrgPostCategory).where(OrgPostCategory.id == cat_id)
    )).scalars().first()
    if not cat:
        raise NotFoundError("Category not found.")
    return cat


@router.get("", response_model=list[CategoryOut], summary="List org categories")
async def list_categories(
    db:      DbDep,
    claims:  AuthDep,
    org_id:  Optional[uuid.UUID] = Query(default=None),
) -> list[CategoryOut]:
    target_org = org_id or claims.org_id
    if not target_org:
        return []
    rows = (await db.execute(
        select(OrgPostCategory)
        .where(OrgPostCategory.org_id == target_org, OrgPostCategory.is_active == True)
        .order_by(OrgPostCategory.sort_order, OrgPostCategory.name)
    )).scalars().all()
    return [CategoryOut.model_validate(c) for c in rows]


@router.post("", response_model=CategoryOut, status_code=status.HTTP_201_CREATED,
             summary="Create category")
async def create_category(body: CategoryCreate, db: DbDep, claims: StaffDep) -> CategoryOut:
    if not claims.org_id:
        from core.exceptions import ForbiddenError
        raise ForbiddenError()
    slug = body.slug or _slugify(body.name)
    existing = (await db.execute(
        select(OrgPostCategory).where(
            OrgPostCategory.org_id == claims.org_id,
            OrgPostCategory.slug == slug,
        )
    )).scalars().first()
    if existing:
        raise ConflictError(f"Category slug '{slug}' already exists.")
    cat = OrgPostCategory(
        org_id=claims.org_id, name=body.name, slug=slug,
        description=body.description, parent_id=body.parent_id,
        sort_order=body.sort_order,
    )
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return CategoryOut.model_validate(cat)


@router.put("/{cat_id}", response_model=CategoryOut, summary="Update category")
async def update_category(cat_id: uuid.UUID, body: CategoryUpdate,
                          db: DbDep, claims: StaffDep) -> CategoryOut:
    cat = await _get_category_or_404(cat_id, db)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(cat, field, value)
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return CategoryOut.model_validate(cat)


@router.delete("/{cat_id}", status_code=status.HTTP_200_OK, summary="Deactivate category")
async def delete_category(cat_id: uuid.UUID, db: DbDep, claims: StaffDep) -> dict:
    cat = await _get_category_or_404(cat_id, db)
    cat.is_active = False
    db.add(cat)
    await db.commit()
    return {"deleted": True, "category_id": str(cat_id)}

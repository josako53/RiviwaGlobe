"""
services/category_service.py
────────────────────────────────────────────────────────────────────────────
Business logic for category CRUD, ML classification, and rate analytics.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Literal, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import FeedbackNotFoundError, NotFoundError, ValidationError
from models.feedback import (
    CategorySource,
    CategoryStatus,
    Feedback,
    FeedbackCategoryDef,
)
from repositories.category_repository import CategoryRepository
from repositories.feedback_repository import FeedbackRepository

PeriodType = Literal["second", "minute", "hour", "day", "week", "month", "quarter", "year"]


class CategoryService:

    def __init__(self, db: AsyncSession) -> None:
        self.repo    = CategoryRepository(db)
        self.fb_repo = FeedbackRepository(db)
        self.db      = db

    # ── CRUD ─────────────────────────────────────────────────────────────────

    async def create(self, data: dict, created_by: uuid.UUID) -> FeedbackCategoryDef:
        slug = data.get("slug", "").strip() or re.sub(r"[^a-z0-9]+", "-", data["name"].lower()).strip("-")
        project_id = uuid.UUID(data["project_id"]) if data.get("project_id") else None

        if await self.repo.get_by_slug(slug, project_id):
            raise ValidationError(
                f"A category with slug '{slug}' already exists "
                f"{'for this project' if project_id else 'platform-wide'}."
            )
        applicable = data.get("applicable_types", ["grievance", "suggestion", "applause"])
        c = FeedbackCategoryDef(
            name             = data["name"],
            slug             = slug,
            description      = data.get("description"),
            project_id       = project_id,
            applicable_types = {"types": applicable},
            source           = CategorySource.MANUAL,
            status           = CategoryStatus.ACTIVE,
            color_hex        = data.get("color_hex"),
            icon             = data.get("icon"),
            display_order    = data.get("display_order", 0),
            created_by_user_id = created_by,
        )
        c = await self.repo.create(c)
        await self.db.commit()
        return c

    async def get_or_404(self, cat_id: uuid.UUID) -> FeedbackCategoryDef:
        c = await self.repo.get_by_id(cat_id)
        if not c:
            raise NotFoundError(message="Category not found.")
        return c

    async def list(self, **kwargs) -> list[FeedbackCategoryDef]:
        feedback_type = kwargs.pop("feedback_type", None)
        items = await self.repo.list(**kwargs)
        if feedback_type:
            items = [c for c in items if c.applies_to(feedback_type)]
        return items

    async def update(self, cat_id: uuid.UUID, data: dict) -> FeedbackCategoryDef:
        c = await self.get_or_404(cat_id)
        if c.source == CategorySource.SYSTEM:
            raise ValidationError("System categories cannot be modified.")
        for field in ("name", "description", "color_hex", "icon", "display_order"):
            if field in data:
                setattr(c, field, data[field])
        if "applicable_types" in data:
            c.applicable_types = {"types": data["applicable_types"]}
        await self.repo.save(c)
        await self.db.commit()
        return c

    async def approve(
        self, cat_id: uuid.UUID, data: dict, by: uuid.UUID
    ) -> FeedbackCategoryDef:
        c = await self.get_or_404(cat_id)
        if c.status != CategoryStatus.PENDING_REVIEW:
            raise ValidationError("Only PENDING_REVIEW categories can be approved.")
        c.status              = CategoryStatus.ACTIVE
        c.reviewed_by_user_id = by
        c.reviewed_at         = datetime.now(timezone.utc)
        c.review_notes        = data.get("notes")
        if data.get("name"): c.name = data["name"]
        if data.get("slug"): c.slug = data["slug"]
        await self.repo.save(c)
        await self.db.commit()
        return c

    async def reject(
        self, cat_id: uuid.UUID, data: dict, by: uuid.UUID
    ) -> FeedbackCategoryDef:
        c = await self.get_or_404(cat_id)
        if c.status != CategoryStatus.PENDING_REVIEW:
            raise ValidationError("Only PENDING_REVIEW categories can be rejected.")
        c.status              = CategoryStatus.REJECTED
        c.reviewed_by_user_id = by
        c.reviewed_at         = datetime.now(timezone.utc)
        c.review_notes        = data.get("notes", "Rejected by reviewer.")
        await self.repo.save(c)
        await self.repo.retag_feedback_from_category(cat_id)
        await self.db.commit()
        return c

    async def deactivate(self, cat_id: uuid.UUID, data: dict) -> FeedbackCategoryDef:
        c = await self.get_or_404(cat_id)
        if c.source == CategorySource.SYSTEM:
            raise ValidationError("System categories cannot be deactivated globally.")
        if c.status != CategoryStatus.ACTIVE:
            raise ValidationError("Only ACTIVE categories can be deactivated.")
        c.status = CategoryStatus.INACTIVE
        c.review_notes = data.get("notes")
        await self.repo.save(c)
        await self.db.commit()
        return c

    async def merge(self, cat_id: uuid.UUID, data: dict) -> FeedbackCategoryDef:
        c      = await self.get_or_404(cat_id)
        target = await self.get_or_404(uuid.UUID(data["merge_into_id"]))
        if not target.is_assignable():
            raise ValidationError("Target category must be ACTIVE and not itself merged.")
        c.merged_into_id = target.id
        c.status         = CategoryStatus.INACTIVE
        c.review_notes   = data.get("notes", f"Merged into '{target.name}'.")
        await self.repo.save(c)
        await self.db.commit()
        return c

    # ── ML classification ─────────────────────────────────────────────────────

    async def classify(
        self, feedback_id: uuid.UUID, data: dict
    ) -> dict:
        fb = await self.fb_repo.get_by_id(feedback_id)
        if not fb:
            raise FeedbackNotFoundError()

        if fb.category_def_id and not data.get("force", False):
            cat = await self.get_or_404(fb.category_def_id)
            return {
                "feedback_id": str(feedback_id),
                "category_def_id": str(fb.category_def_id),
                "category": cat, "confidence": fb.ml_category_confidence,
                "action": "already_classified",
            }

        active_cats = await self.repo.list_active_for_project(fb.project_id)
        cat_list = "\n".join(
            f"- id={c.id} slug={c.slug} name={c.name!r} description={c.description or 'N/A'}"
            for c in active_cats if c.applies_to(fb.feedback_type.value)
        )
        result_data = await self._call_classifier(fb, cat_list)

        confidence   = float(result_data.get("confidence", 0.0))
        matched_id   = result_data.get("matched_category_id")
        new_cat_data = result_data.get("suggested_new_category")
        rationale    = result_data.get("rationale", "")
        action       = "assigned"
        assigned_cat = None

        if matched_id and confidence >= 0.60:
            try:
                assigned_cat = await self.get_or_404(uuid.UUID(matched_id))
                fb.category_def_id        = assigned_cat.id
                fb.ml_category_confidence  = confidence
                fb.ml_category_assigned_at = datetime.now(timezone.utc)
                action = "assigned" if confidence >= 0.85 else "assigned_low_confidence"
            except Exception:
                matched_id = None

        if not matched_id and new_cat_data and confidence >= 0.60:
            new_status = CategoryStatus.ACTIVE if confidence >= 0.85 else CategoryStatus.PENDING_REVIEW
            safe_slug = re.sub(r"[^a-z0-9]+", "-",
                               new_cat_data.get("slug", new_cat_data["name"].lower())).strip("-")
            if not await self.repo.get_by_slug(safe_slug, fb.project_id):
                assigned_cat = FeedbackCategoryDef(
                    name=new_cat_data["name"], slug=safe_slug,
                    description=new_cat_data.get("description"),
                    project_id=fb.project_id,
                    applicable_types={"types": [fb.feedback_type.value]},
                    source=CategorySource.ML, status=new_status,
                    ml_confidence=confidence, ml_model_version="claude-sonnet-4-6",
                    ml_rationale=rationale, triggered_by_feedback_id=fb.id,
                )
                assigned_cat = await self.repo.create(assigned_cat)
                fb.category_def_id        = assigned_cat.id
                fb.ml_category_confidence  = confidence
                fb.ml_category_assigned_at = datetime.now(timezone.utc)
                action = "new_category_created" if new_status == CategoryStatus.ACTIVE else "new_category_pending_review"

        if not assigned_cat:
            other = await self.repo.get_by_slug("other", None)
            if other:
                fb.category_def_id        = other.id
                fb.ml_category_confidence  = confidence
                fb.ml_category_assigned_at = datetime.now(timezone.utc)
                assigned_cat = other
            action = "assigned_other_low_confidence"

        await self.fb_repo.save(fb)
        await self.db.commit()

        return {
            "feedback_id":    str(feedback_id),
            "category_def_id": str(fb.category_def_id) if fb.category_def_id else None,
            "category":       assigned_cat, "confidence": confidence,
            "rationale":      rationale, "action": action,
        }

    async def recategorise(
        self, feedback_id: uuid.UUID, data: dict
    ) -> dict:
        fb = await self.fb_repo.get_by_id(feedback_id)
        if not fb:
            raise FeedbackNotFoundError()
        cat = await self.get_or_404(uuid.UUID(data["category_def_id"]))
        if not cat.is_assignable():
            raise ValidationError("Category is not assignable (inactive, merged, or pending review).")
        if not cat.applies_to(fb.feedback_type.value):
            raise ValidationError(f"Category '{cat.name}' does not apply to {fb.feedback_type.value}.")
        fb.category_def_id        = cat.id
        fb.ml_category_confidence  = None
        fb.ml_category_assigned_at = None
        await self.fb_repo.save(fb)
        await self.db.commit()
        return {"feedback_id": str(fb.id), "category": cat, "action": "manually_assigned"}

    async def _call_classifier(self, fb: Feedback, cat_list: str) -> dict:
        import httpx, json as _json
        prompt = f"""You are a feedback classifier for an infrastructure project management system in Tanzania.
A {fb.feedback_type.value} submission has been received:
Subject: {fb.subject}
Description: {fb.description}
Available categories:
{cat_list or 'No project-specific categories defined yet.'}
Respond ONLY with a JSON object with keys: matched_category_id, confidence, suggested_new_category, rationale."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={"Content-Type": "application/json"},
                    json={"model": "claude-sonnet-4-6", "max_tokens": 500,
                          "system": "Respond ONLY with valid JSON. No prose, no markdown fences.",
                          "messages": [{"role": "user", "content": prompt}]},
                )
                raw  = resp.json()
                text = "".join(b.get("text", "") for b in raw.get("content", []) if b.get("type") == "text")
                return _json.loads(text.strip())
        except Exception:
            return {"matched_category_id": None, "confidence": 0.0,
                    "suggested_new_category": None, "rationale": "Classification unavailable."}

    # ── Rate analytics ────────────────────────────────────────────────────────

    async def rate(
        self, category_id: uuid.UUID, period: PeriodType, **filters
    ) -> dict:
        cat = await self.get_or_404(category_id)
        now = datetime.now(timezone.utc)

        _default_lookback = {
            "second": timedelta(minutes=5), "minute": timedelta(hours=2),
            "hour":   timedelta(hours=48),  "day":    timedelta(days=30),
            "week":   timedelta(days=90),   "month":  timedelta(days=365),
            "quarter": timedelta(days=365), "year":   timedelta(days=365 * 3),
        }
        _max_span = {
            "second": timedelta(hours=1),    "minute": timedelta(hours=24),
            "hour":   timedelta(days=30),    "day":    timedelta(days=365),
            "week":   timedelta(days=365*2), "month":  timedelta(days=365*5),
            "quarter": timedelta(days=365*10), "year": timedelta(days=365*20),
        }
        _poll_seconds = {
            "second": 5, "minute": 30, "hour": 300,
            "day": 3600, "week": 3600, "month": 86400,
            "quarter": 86400, "year": 86400,
        }

        from_date = filters.pop("from_date", None)
        to_date   = filters.pop("to_date", None)
        from_dt   = datetime.fromisoformat(from_date).replace(tzinfo=timezone.utc) if from_date else now - _default_lookback[period]
        to_dt     = datetime.fromisoformat(to_date).replace(tzinfo=timezone.utc) if to_date else now

        if to_dt - from_dt > _max_span[period]:
            raise ValidationError(message=f"Date range too large for period='{period}'.")

        from models.feedback import FeedbackStatus
        open_statuses = {FeedbackStatus.SUBMITTED, FeedbackStatus.ACKNOWLEDGED,
                         FeedbackStatus.IN_REVIEW, FeedbackStatus.ESCALATED, FeedbackStatus.APPEALED}

        items = await self.repo.list_feedback_for_rate(category_id, from_dt, to_dt, **filters)
        total      = len(items)
        open_count = sum(1 for f in items if f.status in open_statuses)

        by_status: Dict[str, int] = {}
        by_type:   Dict[str, int] = {}
        by_period: Dict[str, int] = {}
        for f in items:
            by_status[f.status.value]       = by_status.get(f.status.value, 0) + 1
            by_type[f.feedback_type.value]  = by_type.get(f.feedback_type.value, 0) + 1
            key = self._bucket(f.submitted_at, period)
            by_period[key] = by_period.get(key, 0) + 1

        by_period = dict(sorted(by_period.items()))

        span        = to_dt - from_dt
        prev_count  = await self.repo.count_feedback(category_id, from_dt - span, from_dt, **filters)
        change_pct  = round(((total - prev_count) / prev_count) * 100, 1) if prev_count > 0 else (100.0 if total > 0 else 0.0)

        return {
            "category": cat, "date_range": {"from": from_dt.isoformat(), "to": to_dt.isoformat()},
            "period": period, "total": total, "open_count": open_count,
            "change_pct": change_pct,
            "trend": "up" if change_pct > 5 else ("down" if change_pct < -5 else "stable"),
            "by_period": [{"period": k, "count": v} for k, v in by_period.items()],
            "by_status": [{"status": k, "count": v} for k, v in sorted(by_status.items())],
            "by_type":   [{"type": k, "count": v} for k, v in sorted(by_type.items())],
            "computed_at": now.isoformat(),
            "suggested_poll_seconds": _poll_seconds[period],
            "is_realtime": period in ("second", "minute", "hour"),
        }

    async def summary(
        self, project_id: uuid.UUID, feedback_type: Optional[str] = None,
        from_date: Optional[str] = None, to_date: Optional[str] = None,
    ) -> dict:
        now     = datetime.now(timezone.utc)
        from_dt = datetime.fromisoformat(from_date).replace(tzinfo=timezone.utc) if from_date else now - timedelta(days=30)
        to_dt   = datetime.fromisoformat(to_date).replace(tzinfo=timezone.utc)   if to_date   else now
        cats    = await self.repo.list_active_for_project(project_id)
        result  = []
        for cat in cats:
            total      = await self.repo.count_feedback_in_category_for_project(cat.id, project_id, from_dt, to_dt, feedback_type)
            open_count = await self.repo.count_open_feedback_in_category_for_project(cat.id, project_id, from_dt, to_dt, feedback_type)
            result.append({"category": cat, "total": total, "open_count": open_count})
        result.sort(key=lambda x: x["total"], reverse=True)
        return {
            "project_id": str(project_id),
            "date_range": {"from": from_dt.isoformat(), "to": to_dt.isoformat()},
            "grand_total": sum(r["total"] for r in result),
            "categories": result,
        }

    @staticmethod
    def _bucket(dt: datetime, period: str) -> str:
        if period == "second":  return dt.strftime("%Y-%m-%dT%H:%M:%S")
        if period == "minute":  return dt.strftime("%Y-%m-%dT%H:%M")
        if period == "hour":    return dt.strftime("%Y-%m-%dT%H:00")
        if period == "day":     return dt.strftime("%Y-%m-%d")
        if period == "week":    return f"{dt.isocalendar()[0]}-W{dt.isocalendar()[1]:02d}"
        if period == "month":   return dt.strftime("%Y-%m")
        if period == "quarter": return f"{dt.year}-Q{(dt.month - 1) // 3 + 1}"
        return str(dt.year)

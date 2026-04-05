"""db/init_db.py"""
from __future__ import annotations
import asyncio
import structlog
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import SQLModel, select
from db.session import engine, AsyncSessionLocal

from models.project  import ProjectCache, ProjectStageCache   # noqa: F401
from models.feedback import (                                   # noqa: F401
    Feedback, FeedbackAction, FeedbackEscalation,
    FeedbackResolution, FeedbackAppeal,
    GrievanceCommittee, GrievanceCommitteeMember,
    FeedbackCategoryDef, CategorySource, CategoryStatus,
    ChannelSession,
)

log = structlog.get_logger(__name__)

# ── System category seed data ─────────────────────────────────────────────────
# These are seeded once at startup (idempotent — skipped if slug already exists).
# project_id=NULL → platform-wide, visible for all projects.
_SYSTEM_CATEGORIES = [
    # ── Grievance ───────────────────────────────────────────────────────────
    {"slug": "compensation",       "name": "Compensation",               "types": ["grievance"], "order": 1,  "color": "#E24B4A"},
    {"slug": "resettlement",       "name": "Resettlement",               "types": ["grievance"], "order": 2,  "color": "#D85A30"},
    {"slug": "land-acquisition",   "name": "Land acquisition",           "types": ["grievance"], "order": 3,  "color": "#BA7517"},
    {"slug": "construction-impact","name": "Construction impact",        "types": ["grievance"], "order": 4,  "color": "#854F0B"},
    {"slug": "traffic",            "name": "Traffic and access",         "types": ["grievance"], "order": 5,  "color": "#5F5E5A"},
    {"slug": "worker-rights",      "name": "Worker rights",              "types": ["grievance"], "order": 6,  "color": "#A32D2D"},
    {"slug": "safety-hazard",      "name": "Safety hazard",              "types": ["grievance", "suggestion"], "order": 7, "color": "#E24B4A"},
    {"slug": "environmental",      "name": "Environmental impact",       "types": ["grievance", "suggestion"], "order": 8, "color": "#3B6D11"},
    {"slug": "engagement",         "name": "Engagement and consultation","types": ["grievance", "suggestion"], "order": 9, "color": "#185FA5"},
    {"slug": "design-issue",       "name": "Design issue",               "types": ["grievance", "suggestion"], "order": 10,"color": "#534AB7"},
    {"slug": "project-delay",      "name": "Project delay",              "types": ["grievance"], "order": 11, "color": "#993C1D"},
    {"slug": "corruption",         "name": "Corruption or misconduct",   "types": ["grievance"], "order": 12, "color": "#791F1F"},
    {"slug": "communication",      "name": "Communication",              "types": ["grievance", "suggestion", "applause"], "order": 13, "color": "#0F6E56"},
    {"slug": "accessibility",      "name": "Accessibility",              "types": ["grievance", "suggestion"], "order": 14, "color": "#0C447C"},
    # ── Suggestion ─────────────────────────────────────────────────────────
    {"slug": "design",             "name": "Design improvement",         "types": ["suggestion"], "order": 20, "color": "#534AB7"},
    {"slug": "process",            "name": "Process improvement",        "types": ["suggestion"], "order": 21, "color": "#3C3489"},
    {"slug": "community-benefit",  "name": "Community benefit",          "types": ["suggestion"], "order": 22, "color": "#1D9E75"},
    {"slug": "employment",         "name": "Employment opportunity",     "types": ["suggestion"], "order": 23, "color": "#639922"},
    # ── Applause ───────────────────────────────────────────────────────────
    {"slug": "quality",            "name": "Quality of work",            "types": ["applause"], "order": 30, "color": "#1D9E75"},
    {"slug": "timeliness",         "name": "Timeliness",                 "types": ["applause"], "order": 31, "color": "#0F6E56"},
    {"slug": "staff-conduct",      "name": "Staff conduct",              "types": ["applause"], "order": 32, "color": "#085041"},
    {"slug": "community-impact",   "name": "Community impact",           "types": ["applause"], "order": 33, "color": "#3B6D11"},
    {"slug": "responsiveness",     "name": "Responsiveness",             "types": ["applause"], "order": 34, "color": "#639922"},
    # ── Shared fallback ────────────────────────────────────────────────────
    {"slug": "safety",             "name": "Safety",                     "types": ["grievance", "suggestion", "applause"], "order": 40, "color": "#E24B4A"},
    {"slug": "other",              "name": "Other",                      "types": ["grievance", "suggestion", "applause"], "order": 99, "color": "#888780"},
]


async def seed_system_categories() -> None:
    """
    Idempotent: seeds system categories on first boot.
    Skips any category whose slug already exists as a platform-wide (project_id=NULL) category.
    """
    async with AsyncSessionLocal() as db:
        for cat_data in _SYSTEM_CATEGORIES:
            existing = await db.execute(
                select(FeedbackCategoryDef).where(
                    FeedbackCategoryDef.slug       == cat_data["slug"],
                    FeedbackCategoryDef.project_id == None,
                )
            )
            if existing.scalar_one_or_none():
                continue
            cat = FeedbackCategoryDef(
                name             = cat_data["name"],
                slug             = cat_data["slug"],
                description      = None,
                project_id       = None,
                applicable_types = {"types": cat_data["types"]},
                source           = CategorySource.SYSTEM,
                status           = CategoryStatus.ACTIVE,
                color_hex        = cat_data.get("color"),
                display_order    = cat_data.get("order", 99),
            )
            db.add(cat)
        await db.commit()
    log.info("feedback.categories.seeded")


async def init_db(max_retries: int = 5, initial_delay: float = 2.0, backoff_factor: float = 2.0) -> None:
    delay    = initial_delay
    last_exc = None
    for attempt in range(1, max_retries + 1):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(SQLModel.metadata.create_all)
            log.info("feedback.db.tables_created")
            # Seed system categories after tables exist
            await seed_system_categories()
            return
        except (SQLAlchemyError, OSError) as exc:
            last_exc = exc
            log.warning("feedback.db.init.retry", attempt=attempt, delay=delay, error=str(exc))
            if attempt < max_retries:
                await asyncio.sleep(delay)
                delay *= backoff_factor
    raise RuntimeError(f"feedback_service: database unreachable after {max_retries} attempts.") from last_exc


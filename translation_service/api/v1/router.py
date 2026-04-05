# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  translation_service  |  Port: 8050  |  DB: translation_db (5438)
# FILE     :  api/v1/router.py
# ───────────────────────────────────────────────────────────────────────────
"""api/v1/router.py — Aggregates all translation_service API routers."""
from __future__ import annotations

from fastapi import APIRouter

from api.v1 import translate

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(translate.router)

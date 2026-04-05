"""api/v1/router.py — Aggregates all API v1 routers."""
from __future__ import annotations

from fastapi import APIRouter

from api.v1 import discover, indexing, recommendations

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(recommendations.router)
api_v1_router.include_router(discover.router)
api_v1_router.include_router(indexing.router)

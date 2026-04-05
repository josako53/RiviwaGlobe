# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  notification_service  |  Port: 8060  |  DB: notification_db (5437)
# FILE     :  api/v1/router.py
# ───────────────────────────────────────────────────────────────────────────
"""api/v1/router.py — Aggregates all notification_service API routers."""
from __future__ import annotations

from fastapi import APIRouter

from api.v1 import devices, internal, notifications, preferences, templates, webhooks

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(notifications.router)
api_v1_router.include_router(preferences.router)
api_v1_router.include_router(devices.router)
api_v1_router.include_router(internal.router)
api_v1_router.include_router(templates.router)
api_v1_router.include_router(webhooks.router)

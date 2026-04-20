# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  riviwa_auth_service  |  Port: 8000  |  DB: auth_db (5433)
# FILE     :  api/v1/router.py
# ───────────────────────────────────────────────────────────────────────────
"""
app/api/v1/router.py
═══════════════════════════════════════════════════════════════════════════════
Aggregates all API v1 routers into a single APIRouter mounted at /api/v1.
"""
from __future__ import annotations

from fastapi import APIRouter

from api.v1 import addresses, admin_dashboard, auth, channel_auth, checklists, departments, internal_orgs, organisations, org_extended, password, projects, register, system_settings, users, webhooks

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth.router)
api_v1_router.include_router(channel_auth.router)
api_v1_router.include_router(register.router)
api_v1_router.include_router(password.router)
api_v1_router.include_router(users.router)
api_v1_router.include_router(organisations.router)
api_v1_router.include_router(departments.router)
api_v1_router.include_router(org_extended.router)
api_v1_router.include_router(projects.router)
api_v1_router.include_router(checklists.router)
api_v1_router.include_router(webhooks.router)
api_v1_router.include_router(admin_dashboard.router)
api_v1_router.include_router(system_settings.router)
api_v1_router.include_router(addresses.router)
api_v1_router.include_router(internal_orgs.router)

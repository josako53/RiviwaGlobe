"""api/v1/router.py — analytics_service"""
# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  analytics_service     |  Port: 8095
# FILE     :  api/v1/router.py
# ───────────────────────────────────────────────────────────────────────────
from fastapi import APIRouter

from api.v1 import ai_insights, feedback, grievances, staff, suggestions

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(feedback.router)
api_v1_router.include_router(grievances.router)
api_v1_router.include_router(suggestions.router)
api_v1_router.include_router(staff.router)
api_v1_router.include_router(ai_insights.router)

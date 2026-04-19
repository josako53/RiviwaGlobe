# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  feedback_service     |  Port: 8090  |  DB: feedback_db (5434)
# FILE     :  api/v1/router.py
# ───────────────────────────────────────────────────────────────────────────
"""api/v1/router.py — feedback_service"""
from fastapi import APIRouter
from api.v1 import actions, categories, channels, committees, consumer, escalation_paths, feedback, reports, voice

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(feedback.router)
api_v1_router.include_router(actions.router)
api_v1_router.include_router(categories.router)
api_v1_router.include_router(channels.router)
api_v1_router.include_router(committees.router)
api_v1_router.include_router(escalation_paths.router)
api_v1_router.include_router(consumer.router)
api_v1_router.include_router(reports.router)
api_v1_router.include_router(voice.router)

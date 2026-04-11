"""api/v1/router.py — ai_service"""
from fastapi import APIRouter
from api.v1 import chat, webhooks, admin, internal

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(chat.router)
api_v1_router.include_router(webhooks.router)
api_v1_router.include_router(admin.router)
api_v1_router.include_router(internal.router)

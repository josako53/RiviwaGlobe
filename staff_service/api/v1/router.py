"""api/v1/router.py — Aggregate all v1 routers."""
from fastapi import APIRouter

from api.v1.public import router as public_router
from api.v1.admin import router as admin_router
from api.v1.analytics import router as analytics_router
from api.v1.internal import router as internal_router

api_router = APIRouter()
api_router.include_router(public_router)
api_router.include_router(admin_router)
api_router.include_router(analytics_router)
api_router.include_router(internal_router)

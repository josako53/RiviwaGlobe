"""api/v1/router.py — Aggregate all routers under /api/v1."""
from fastapi import APIRouter
from api.v1.plans import router as plans_router
from api.v1.subscriptions import router as subscriptions_router
from api.v1.checkout import router as checkout_router
from api.v1.promotions import router as promotions_router
from api.v1.sales import router as sales_router
from api.v1.admin import router as admin_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(plans_router)
api_v1_router.include_router(subscriptions_router)
api_v1_router.include_router(checkout_router)
api_v1_router.include_router(promotions_router)
api_v1_router.include_router(sales_router)
api_v1_router.include_router(admin_router)

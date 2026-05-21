"""api/v1/router.py — payment_service"""
from fastapi import APIRouter
from api.v1 import disbursements, payments, webhooks

api_v1_router = APIRouter(prefix="/api/v1")
# disbursements MUST come before payments — its static prefix /payments/disbursements
# would otherwise be swallowed by payments' dynamic route GET /payments/{payment_id}
api_v1_router.include_router(disbursements.router)
api_v1_router.include_router(payments.router)
api_v1_router.include_router(webhooks.router)

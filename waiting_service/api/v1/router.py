from fastapi import APIRouter
from api.v1 import admin, internal, queue, staff, analytics, sms

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(internal.internal_router)
api_v1_router.include_router(admin.admin_router)
api_v1_router.include_router(queue.queue_router)
api_v1_router.include_router(staff.staff_router)
api_v1_router.include_router(analytics.analytics_router)
api_v1_router.include_router(sms.sms_router)

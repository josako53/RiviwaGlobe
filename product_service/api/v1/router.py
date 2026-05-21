from fastapi import APIRouter
from .internal import router as internal_router
from .products import router as products_router
from .public import router as public_router

api_router = APIRouter()
api_router.include_router(products_router)
api_router.include_router(internal_router)
api_router.include_router(public_router)

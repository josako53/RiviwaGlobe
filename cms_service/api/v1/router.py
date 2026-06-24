from fastapi import APIRouter
from api.v1.posts import router as posts_router
from api.v1.categories import router as categories_router
from api.v1.comments import router as comments_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(posts_router)
api_router.include_router(categories_router)
api_router.include_router(comments_router)

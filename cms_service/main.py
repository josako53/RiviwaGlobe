"""main.py — CMS service FastAPI application."""
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

import db.base  # noqa: F401 — registers all models in SQLModel.metadata

from core.config import settings
from core.exceptions import AppError
from db.session import engine
from sqlmodel import SQLModel

log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("cms_service.startup.begin")

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    log.info("cms_service.startup.db_ready")

    from events.producer import get_producer
    producer = await get_producer()
    await producer.start()
    app.state.producer = producer
    log.info("cms_service.startup.kafka_producer_ready")

    log.info("cms_service.startup.complete", port=8150)
    yield

    log.info("cms_service.shutdown.begin")
    await app.state.producer.stop()
    await engine.dispose()
    log.info("cms_service.shutdown.complete")


app = FastAPI(
    title="Riviwa CMS Service",
    description=(
        "Organisation-scoped Content Management System. "
        "Manage posts, news, announcements, blog articles, events, and policy updates. "
        "Full publish workflow: Draft → Review → Scheduled → Published → Archived."
    ),
    version="1.0.0",
    docs_url=None if settings.ENVIRONMENT == "production" else "/docs",
    redoc_url=None if settings.ENVIRONMENT == "production" else "/redoc",
    openapi_url=None if settings.ENVIRONMENT == "production" else "/openapi.json",
    lifespan=lifespan,
)

if settings.ENVIRONMENT != "production":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=exc.to_response_body())


@app.exception_handler(PydanticValidationError)
async def validation_error_handler(request: Request, exc: PydanticValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": "VALIDATION_ERROR", "message": "Request validation failed",
                 "detail": exc.errors()},
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    log.error("cms_service.unhandled_error", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"},
    )


from api.v1.router import api_router  # noqa: E402
app.include_router(api_router)


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "service": settings.SERVICE_NAME}

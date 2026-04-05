"""core/config.py — Recommendation service configuration."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    # ── Service ───────────────────────────────────────────────────────────────
    SERVICE_NAME: str = "recommendation_service"
    ENVIRONMENT: str = "production"
    DEBUG: bool = False

    # ── Database (PostGIS) ────────────────────────────────────────────────────
    RECOMMENDATION_DB_HOST: str = "recommendation_db"
    DB_PORT: int = 5432
    RECOMMENDATION_DB_USER: str = "rec_admin"
    RECOMMENDATION_DB_PASSWORD: str = "rec_pass_321"
    RECOMMENDATION_DB_NAME: str = "recommendation_db"

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.RECOMMENDATION_DB_USER}:"
            f"{self.RECOMMENDATION_DB_PASSWORD}@{self.RECOMMENDATION_DB_HOST}:"
            f"{self.DB_PORT}/{self.RECOMMENDATION_DB_NAME}"
        )

    @property
    def SYNC_DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg://{self.RECOMMENDATION_DB_USER}:"
            f"{self.RECOMMENDATION_DB_PASSWORD}@{self.RECOMMENDATION_DB_HOST}:"
            f"{self.DB_PORT}/{self.RECOMMENDATION_DB_NAME}"
        )

    # ── JWT verification (mirrors auth service signing key) ───────────────────
    AUTH_SECRET_KEY: str = "change-me"
    AUTH_ALGORITHM: str = "HS256"

    # ── Kafka ─────────────────────────────────────────────────────────────────
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka-1:9092"

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://redis:6379/5"
    CACHE_TTL_RECOMMENDATIONS: int = 3600
    CACHE_TTL_CANDIDATES: int = 7200

    # ── Qdrant ────────────────────────────────────────────────────────────────
    QDRANT_HOST: str = "qdrant"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION: str = "riviwa_entities"

    # ── Embedding model ───────────────────────────────────────────────────────
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIM: int = 384
    EMBEDDING_DEVICE: str = "cpu"

    # ── Scoring weights (must sum to 1.0) ─────────────────────────────────────
    WEIGHT_SEMANTIC: float = 0.35
    WEIGHT_TAG_OVERLAP: float = 0.25
    WEIGHT_GEO_PROXIMITY: float = 0.25
    WEIGHT_RECENCY: float = 0.15

    # ── Geo tiers (km) ───────────────────────────────────────────────────────
    GEO_TIER_CITY: float = 10.0
    GEO_TIER_DISTRICT: float = 50.0
    GEO_TIER_REGION: float = 200.0
    GEO_TIER_COUNTRY: float = 800.0

    # ── Recency decay ────────────────────────────────────────────────────────
    RECENCY_LAMBDA: float = 0.01

    # ── Service-to-service ───────────────────────────────────────────────────
    INTERNAL_SERVICE_KEY: str = "change-me"
    AUTH_SERVICE_URL: str = "http://riviwa_auth_service:8000"


settings = Settings()

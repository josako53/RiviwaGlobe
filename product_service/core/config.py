from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    # ── Service ──────────────────────────────────────────────────
    SERVICE_NAME: str = "product_service"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # ── Product DB ───────────────────────────────────────────────
    PRODUCT_DB_HOST: str = "product_db"
    PRODUCT_DB_PORT: int = 5432
    PRODUCT_DB_USER: str = "product_admin"
    PRODUCT_DB_PASSWORD: str = "product_pass_123"
    PRODUCT_DB_NAME: str = "product_db"

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.PRODUCT_DB_USER}:{self.PRODUCT_DB_PASSWORD}"
            f"@{self.PRODUCT_DB_HOST}:{self.PRODUCT_DB_PORT}/{self.PRODUCT_DB_NAME}"
        )

    @property
    def SYNC_DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg://{self.PRODUCT_DB_USER}:{self.PRODUCT_DB_PASSWORD}"
            f"@{self.PRODUCT_DB_HOST}:{self.PRODUCT_DB_PORT}/{self.PRODUCT_DB_NAME}"
        )

    # ── JWT (validated against auth_service-signed tokens) ───────
    AUTH_SECRET_KEY: str = "change-me-in-env"
    AUTH_ALGORITHM: str = "HS256"

    # ── Kafka ────────────────────────────────────────────────────
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka-1:9092"
    KAFKA_PRODUCT_TOPIC: str = "riviwa.product.events"
    KAFKA_ORG_TOPIC: str = "riviwa.organisation.events"
    KAFKA_USER_TOPIC: str = "riviwa.user.events"
    KAFKA_CONSUMER_GROUP: str = "product_service_group"

    # ── Service-to-Service ───────────────────────────────────────
    INTERNAL_SERVICE_KEY: str = "change-me-in-production"
    AUTH_SERVICE_URL: str = "http://riviwa_auth_service:8000"
    AI_SERVICE_URL: str = "http://ai_service:8085"

    # ── Redis ────────────────────────────────────────────────────
    REDIS_URL: str = "redis://redis:6379/8"

    # ── Storage (MinIO — for product images) ─────────────────────
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    IMAGES_BUCKET: str = "riviwa-images"
    MINIO_USE_SSL: bool = False


settings = Settings()

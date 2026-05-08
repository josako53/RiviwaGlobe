from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    # ── Service ──────────────────────────────────────────────────────────────
    SERVICE_NAME: str = "staff_service"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # ── Staff DB ─────────────────────────────────────────────────────────────
    STAFF_DB_HOST: str = "staff_db"
    DB_PORT: int = 5432
    STAFF_DB_USER: str = "staff_admin"
    STAFF_DB_PASSWORD: str = "staff_pass_135"
    STAFF_DB_NAME: str = "staff_db"

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.STAFF_DB_USER}:{self.STAFF_DB_PASSWORD}"
            f"@{self.STAFF_DB_HOST}:{self.DB_PORT}/{self.STAFF_DB_NAME}"
        )

    @property
    def SYNC_DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg://{self.STAFF_DB_USER}:{self.STAFF_DB_PASSWORD}"
            f"@{self.STAFF_DB_HOST}:{self.DB_PORT}/{self.STAFF_DB_NAME}"
        )

    # ── JWT (validated against auth_service-signed tokens) ───────────────────
    AUTH_SECRET_KEY: str = "change-me-in-env"
    AUTH_ALGORITHM: str = "HS256"

    # ── Kafka ─────────────────────────────────────────────────────────────────
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka-1:9092"
    KAFKA_STAFF_TOPIC: str = "riviwa.staff.events"
    KAFKA_ORG_TOPIC: str = "riviwa.organisation.events"
    KAFKA_CONSUMER_GROUP: str = "staff_service_group"

    # ── Service-to-Service ────────────────────────────────────────────────────
    INTERNAL_SERVICE_KEY: str = "change-me-in-production"
    AUTH_SERVICE_URL: str = "http://riviwa_auth_service:8000"

    # ── Redis (DB 10 for rate limiting) ───────────────────────────────────────
    REDIS_URL: str = "redis://redis:6379/10"

    # ── Storage (MinIO) ───────────────────────────────────────────────────────
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    STAFF_BUCKET: str = "riviwa-staff"
    MINIO_USE_SSL: bool = False


settings = Settings()

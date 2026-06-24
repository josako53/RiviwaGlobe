from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    SERVICE_NAME: str = "cms_service"
    ENVIRONMENT:  str = "development"
    DEBUG:        bool = False

    # ── CMS DB ───────────────────────────────────────────────────────────────
    CMS_DB_HOST:     str = "cms_db"
    DB_PORT:         int = 5432
    CMS_DB_USER:     str = "cms_admin"
    CMS_DB_PASSWORD: str = "cms_pass_150"
    CMS_DB_NAME:     str = "cms_db"

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.CMS_DB_USER}:{self.CMS_DB_PASSWORD}"
            f"@{self.CMS_DB_HOST}:{self.DB_PORT}/{self.CMS_DB_NAME}"
        )

    @property
    def SYNC_DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg://{self.CMS_DB_USER}:{self.CMS_DB_PASSWORD}"
            f"@{self.CMS_DB_HOST}:{self.DB_PORT}/{self.CMS_DB_NAME}"
        )

    # ── JWT (validated against auth_service-signed tokens) ───────────────────
    AUTH_SECRET_KEY: str = "change-me-in-env"
    AUTH_ALGORITHM:  str = "HS256"

    # ── Kafka ─────────────────────────────────────────────────────────────────
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka-1:9092"
    KAFKA_CMS_TOPIC:         str = "riviwa.cms.events"
    KAFKA_ORG_TOPIC:         str = "riviwa.organisation.events"
    KAFKA_CONSUMER_GROUP:    str = "cms_service_group"

    # ── Service-to-Service ────────────────────────────────────────────────────
    INTERNAL_SERVICE_KEY:  str = "change-me-in-production"
    AUTH_SERVICE_URL:      str = "http://riviwa_auth_service:8000"
    FEEDBACK_SERVICE_URL:  str = "http://feedback_service:8090"
    AI_SERVICE_URL:        str = "http://ai_service:8085"

    # ── Storage (MinIO) ───────────────────────────────────────────────────────
    MINIO_ENDPOINT:   str  = "minio:9000"
    MINIO_ACCESS_KEY: str  = "minioadmin"
    MINIO_SECRET_KEY: str  = "minioadmin"
    CMS_BUCKET:       str  = "riviwa-cms"
    MINIO_USE_SSL:    bool = False


settings = Settings()

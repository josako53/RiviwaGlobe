# core/config.py
# All environment variables for the stakeholder_service

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    # ── Database ──────────────────────────────────────────────────────────────
    STAKEHOLDER_DB_HOST:     str = Field(default="stakeholder_db")
    DB_PORT:                 int = Field(default=5432)
    STAKEHOLDER_DB_USER:     str = Field(default="stakeholder_admin")
    STAKEHOLDER_DB_PASSWORD: str = Field(default="stakeholder_pass_123")
    STAKEHOLDER_DB_NAME:     str = Field(default="stakeholder_db")

    # ── App ───────────────────────────────────────────────────────────────────
    API_V1_STR:                      str = "/api/v1"
    STAKEHOLDER_SERVICE_NAME:        str = Field(default="stakeholder_service")
    APP_BASE_URL:                    str = Field(default="https://riviwa.com")

    # ── Kafka ─────────────────────────────────────────────────────────────────
    KAFKA_BOOTSTRAP_SERVERS: str = Field(
        default="kafka-1:9092",
        description="Kafka bootstrap servers. Single node in dev, cluster in prod.",
    )

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL: str = Field(
        default="redis://redis:6379/3",
        description=(
            "Redis DB 3 for stakeholder_service — avoids collision with "
            "auth_service (DB 0), Celery broker (DB 1), Celery results (DB 2)."
        ),
    )

    # ── Auth service integration ───────────────────────────────────────────────
    # Base URL for internal calls to auth_service (e.g. address creation).
    AUTH_SERVICE_URL: str = Field(
        default="http://riviwa_auth_service:8000",
        description="Internal base URL for auth_service. Used for cross-service address creation.",
    )
    # Shared secret for internal service-to-service calls.
    INTERNAL_SERVICE_KEY: str = Field(
        default="internal_service_key_placeholder",
        description="Passed as X-Internal-Service-Key header on service-to-service calls.",
    )
    # Used to validate JWTs issued by auth_service on protected endpoints.
    # Must match auth_service SECRET_KEY and ALGORITHM exactly.
    AUTH_SECRET_KEY: str = Field(
        default="8f3d951a56fa9820abee2a70d9d44acfbe7965ef8562fd40b489c8759bfa2cfe",
        description=(
            "Shared JWT signing secret with auth_service. "
            "Rotate both at the same time in production."
        ),
    )
    AUTH_ALGORITHM: str = Field(default="HS256")

    # ── Runtime environment ────────────────────────────────────────────────────
    ENVIRONMENT: str = Field(default="production")
    DEBUG:       bool = Field(default=False)

    # ── Computed DB URLs ──────────────────────────────────────────────────────
    @property
    def SYNC_DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg://{self.STAKEHOLDER_DB_USER}:{self.STAKEHOLDER_DB_PASSWORD}"
            f"@{self.STAKEHOLDER_DB_HOST}:{self.DB_PORT}/{self.STAKEHOLDER_DB_NAME}"
        )

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.STAKEHOLDER_DB_USER}:{self.STAKEHOLDER_DB_PASSWORD}"
            f"@{self.STAKEHOLDER_DB_HOST}:{self.DB_PORT}/{self.STAKEHOLDER_DB_NAME}"
        )


settings = Settings()

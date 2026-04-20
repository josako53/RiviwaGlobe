# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  analytics_service     |  Port: 8095  |  DB: analytics_db
# FILE     :  core/config.py
# ───────────────────────────────────────────────────────────────────────────
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    # ── Analytics DB (own database) ───────────────────────────────────────────
    ANALYTICS_DB_HOST:     str = Field(default="analytics_db")
    ANALYTICS_DB_PORT:     int = Field(default=5432)
    ANALYTICS_DB_USER:     str = Field(default="analytics_admin")
    ANALYTICS_DB_PASSWORD: str = Field(default="analytics_pass_123")
    ANALYTICS_DB_NAME:     str = Field(default="analytics_db")

    # ── Feedback DB (read-only cross-service analytics) ───────────────────────
    FEEDBACK_DB_HOST:     str = Field(default="feedback_db")
    FEEDBACK_DB_PORT:     int = Field(default=5432)
    FEEDBACK_DB_USER:     str = Field(default="feedback_admin")
    FEEDBACK_DB_PASSWORD: str = Field(default="feedback_pass_456")
    FEEDBACK_DB_NAME:     str = Field(default="feedback_db")

    # ── App ───────────────────────────────────────────────────────────────────
    API_V1_STR:              str = "/api/v1"
    ANALYTICS_SERVICE_NAME:  str = Field(default="analytics_service")

    # ── JWT — validates tokens from auth_service ───────────────────────────────
    AUTH_SECRET_KEY: str = Field(
        default="8f3d951a56fa9820abee2a70d9d44acfbe7965ef8562fd40b489c8759bfa2cfe",
    )
    AUTH_ALGORITHM: str = Field(default="HS256")

    # ── Service-to-service auth ───────────────────────────────────────────────
    INTERNAL_SERVICE_KEY: str = Field(
        default="change-me-in-production",
        description="Shared secret for internal service calls. Must match AUTH_SERVICE INTERNAL_SERVICE_KEY.",
    )
    AUTH_SERVICE_URL: str = Field(
        default="http://riviwa_auth_service:8000",
        description="Base URL of auth_service for internal org context lookups.",
    )

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL: str = Field(default="redis://redis:6379/4")

    # ── Groq LLM (AI Insights) ────────────────────────────────────────────────
    GROQ_API_KEY:   str = Field(default="", description="Groq API key for LLM inference.")
    GROQ_MODEL:     str = Field(default="llama-3.3-70b-versatile")
    GROQ_BASE_URL:  str = Field(default="https://api.groq.com/openai/v1")

    # ── Runtime ───────────────────────────────────────────────────────────────
    ENVIRONMENT: str  = Field(default="production")
    DEBUG:       bool = Field(default=False)

    # ── DB URL properties ─────────────────────────────────────────────────────
    @property
    def ASYNC_ANALYTICS_DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.ANALYTICS_DB_USER}:{self.ANALYTICS_DB_PASSWORD}"
            f"@{self.ANALYTICS_DB_HOST}:{self.ANALYTICS_DB_PORT}/{self.ANALYTICS_DB_NAME}"
        )

    @property
    def SYNC_ANALYTICS_DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg://{self.ANALYTICS_DB_USER}:{self.ANALYTICS_DB_PASSWORD}"
            f"@{self.ANALYTICS_DB_HOST}:{self.ANALYTICS_DB_PORT}/{self.ANALYTICS_DB_NAME}"
        )

    @property
    def ASYNC_FEEDBACK_DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.FEEDBACK_DB_USER}:{self.FEEDBACK_DB_PASSWORD}"
            f"@{self.FEEDBACK_DB_HOST}:{self.FEEDBACK_DB_PORT}/{self.FEEDBACK_DB_NAME}"
        )


settings = Settings()

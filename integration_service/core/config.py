from __future__ import annotations
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    # ── Database ──────────────────────────────────────────────────────────────
    INTEGRATION_DB_HOST:     str = Field(default="integration_db")
    DB_PORT:                 int = Field(default=5432)
    INTEGRATION_DB_USER:     str = Field(default="integration_admin")
    INTEGRATION_DB_PASSWORD: str = Field(default="integration_pass_999")
    INTEGRATION_DB_NAME:     str = Field(default="integration_db")

    # ── App ───────────────────────────────────────────────────────────────────
    ENVIRONMENT:   str  = Field(default="production")
    DEBUG:         bool = Field(default=False)

    # ── JWT (signs integration access tokens) ─────────────────────────────────
    # Uses the same key as auth_service so tokens are cross-verifiable
    AUTH_SECRET_KEY: str = Field(
        default="8f3d951a56fa9820abee2a70d9d44acfbe7965ef8562fd40b489c8759bfa2cfe"
    )
    AUTH_ALGORITHM: str = Field(default="HS256")

    # ── Token TTLs ────────────────────────────────────────────────────────────
    ACCESS_TOKEN_TTL_SECONDS:  int = Field(default=900,     description="15 minutes")
    REFRESH_TOKEN_TTL_SECONDS: int = Field(default=2592000, description="30 days")
    AUTH_CODE_TTL_SECONDS:     int = Field(default=600,     description="10 minutes")
    CONTEXT_SESSION_TTL_SECONDS: int = Field(default=1800,  description="30 minutes")

    # ── Encryption key for at-rest data (context sessions, endpoint creds) ────
    # 32-byte base64url key. Generate: python -c "import secrets,base64; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"
    ENCRYPTION_KEY: str = Field(
        default="CHANGE_ME_32_BYTE_BASE64URL_KEY_HERE",
        description="AES-256-GCM key for encrypting sensitive fields at rest",
    )

    # ── Service-to-service ────────────────────────────────────────────────────
    INTERNAL_SERVICE_KEY:  str = Field(default="change-me-in-production")
    AUTH_SERVICE_URL:      str = Field(default="http://riviwa_auth_service:8000")
    FEEDBACK_SERVICE_URL:  str = Field(default="http://feedback_service:8090")

    # ── Redis (rate limiting + token deny-list) ───────────────────────────────
    REDIS_URL: str = Field(default="redis://redis:6379/7",
                           description="DB 7 reserved for integration_service")

    # ── Webhook delivery ──────────────────────────────────────────────────────
    WEBHOOK_TIMEOUT_SECS:    int = Field(default=10)
    WEBHOOK_MAX_RETRIES:     int = Field(default=3)
    WEBHOOK_RETRY_DELAYS:    list = Field(default=[30, 300, 1800],
                                          description="Backoff delays in seconds")

    # ── Rate limiting defaults ────────────────────────────────────────────────
    DEFAULT_RATE_LIMIT_PER_MINUTE: int = Field(default=60)
    DEFAULT_RATE_LIMIT_PER_DAY:    int = Field(default=10000)

    # ── Widget embed base URL ─────────────────────────────────────────────────
    RIVIWA_WIDGET_BASE_URL: str = Field(
        default="https://widget.riviwa.com",
        description="Base URL served for JS widget snippets and embed links",
    )

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.INTEGRATION_DB_USER}:{self.INTEGRATION_DB_PASSWORD}"
            f"@{self.INTEGRATION_DB_HOST}:{self.DB_PORT}/{self.INTEGRATION_DB_NAME}"
        )

    @property
    def SYNC_DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg://{self.INTEGRATION_DB_USER}:{self.INTEGRATION_DB_PASSWORD}"
            f"@{self.INTEGRATION_DB_HOST}:{self.DB_PORT}/{self.INTEGRATION_DB_NAME}"
        )


settings = Settings()

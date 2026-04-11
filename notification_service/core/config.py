# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  notification_service  |  Port: 8060  |  DB: notification_db (5437)
# FILE     :  core/config.py
# ───────────────────────────────────────────────────────────────────────────
from __future__ import annotations
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    # ── Database ──────────────────────────────────────────────────────────────
    NOTIFICATION_DB_HOST:     str = Field(default="notification_db")
    DB_PORT:                  int = Field(default=5432)
    NOTIFICATION_DB_USER:     str = Field(default="notif_admin")
    NOTIFICATION_DB_PASSWORD: str = Field(default="notif_pass_789")
    NOTIFICATION_DB_NAME:     str = Field(default="notification_db")

    @property
    def SYNC_DATABASE_URL(self) -> str:
        """Used by Alembic (synchronous psycopg driver)."""
        return (
            f"postgresql+psycopg://{self.NOTIFICATION_DB_USER}:{self.NOTIFICATION_DB_PASSWORD}"
            f"@{self.NOTIFICATION_DB_HOST}:{self.DB_PORT}/{self.NOTIFICATION_DB_NAME}"
        )

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        """Used by FastAPI / SQLAlchemy async engine."""
        return (
            f"postgresql+asyncpg://{self.NOTIFICATION_DB_USER}:{self.NOTIFICATION_DB_PASSWORD}"
            f"@{self.NOTIFICATION_DB_HOST}:{self.DB_PORT}/{self.NOTIFICATION_DB_NAME}"
        )

    # ── App ───────────────────────────────────────────────────────────────────
    ENVIRONMENT:  str = Field(default="production")
    DEBUG:        bool = Field(default=False)
    SERVICE_NAME: str = Field(default="notification_service")

    # ── Kafka ─────────────────────────────────────────────────────────────────
    KAFKA_BOOTSTRAP_SERVERS: str = Field(default="kafka-1:9092")

    # ── JWT verification (shared with auth service) ───────────────────────────
    AUTH_SECRET_KEY: str = Field(default="change-me-in-env")
    AUTH_ALGORITHM:  str = Field(default="HS256")

    # ── Internal service key (same secret as other services) ──────────────────
    INTERNAL_SERVICE_KEY: str = Field(default="change-me-in-env")

    # ── Delivery retry config ─────────────────────────────────────────────────
    MAX_RETRIES:          int   = Field(default=3)
    RETRY_BASE_DELAY_SEC: float = Field(default=60.0)   # first retry after 60s
    RETRY_BACKOFF_FACTOR: float = Field(default=2.0)    # 60s → 120s → 240s

    # ── Rate limiting (per user per notification_type per hour) ───────────────
    RATE_LIMIT_MAX:       int = Field(default=5)
    RATE_LIMIT_WINDOW_SEC:int = Field(default=3600)

    # ── Redis (rate limiting + dedup cache) ───────────────────────────────────
    REDIS_URL: str = Field(default="redis://redis:6379/3")

    # ── Push — Firebase Cloud Messaging ──────────────────────────────────────
    FCM_SERVICE_ACCOUNT_JSON: str = Field(
        default="",
        description="JSON string of the Firebase service account credentials. Set in .env.",
    )
    FCM_PROJECT_ID: str = Field(default="")

    # ── Push — Apple Push Notification service ────────────────────────────────
    APNS_KEY_ID:      str = Field(default="")
    APNS_TEAM_ID:     str = Field(default="")
    APNS_AUTH_KEY:    str = Field(default="")    # PEM content or path
    APNS_BUNDLE_ID:   str = Field(default="com.riviwa.app")
    APNS_USE_SANDBOX: bool = Field(default=False)

    # ── SMS — Africa's Talking ────────────────────────────────────────────────
    AT_API_KEY:     str = Field(default="")
    AT_USERNAME:    str = Field(default="sandbox")
    AT_SENDER_ID:   str = Field(default="RIVIWA")

    # ── SMS — Twilio (fallback) ───────────────────────────────────────────────
    TWILIO_ACCOUNT_SID:    str = Field(default="")
    TWILIO_AUTH_TOKEN:     str = Field(default="")
    TWILIO_FROM_NUMBER:    str = Field(default="")

    # ── WhatsApp — Meta Cloud API ─────────────────────────────────────────────
    META_WHATSAPP_TOKEN:       str = Field(default="")
    META_WHATSAPP_PHONE_ID:    str = Field(default="")

    # ── Email — SendGrid ──────────────────────────────────────────────────────
    SENDGRID_API_KEY:  str = Field(default="")
    EMAIL_FROM:        str = Field(default="noreply@riviwa.com")
    EMAIL_FROM_NAME:   str = Field(default="Riviwa Platform")

    # ── Email — SMTP fallback ─────────────────────────────────────────────────
    SMTP_HOST:     str = Field(default="")
    SMTP_PORT:     int = Field(default=587)
    SMTP_USERNAME: str = Field(default="")
    SMTP_PASSWORD: str = Field(default="")
    SMTP_USE_TLS:  bool = Field(default=True)

    @property
    def is_staging(self) -> bool:
        return self.ENVIRONMENT in ("staging", "development")


settings = Settings()

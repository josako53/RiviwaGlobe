"""core/config.py — payment_service"""
from __future__ import annotations
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://payment_user:payment_password@payment_db:5432/payment_db"
    )

    # ── App ───────────────────────────────────────────────────────────────────
    PORT:             int  = Field(default=8040)
    ENVIRONMENT:      str  = Field(default="production")
    DEBUG:            bool = Field(default=False)

    # ── JWT — validates tokens from auth_service ──────────────────────────────
    AUTH_SECRET_KEY: str = Field(
        default="8f3d951a56fa9820abee2a70d9d44acfbe7965ef8562fd40b489c8759bfa2cfe"
    )
    AUTH_ALGORITHM: str = Field(default="HS256")

    # ── Kafka ─────────────────────────────────────────────────────────────────
    KAFKA_BOOTSTRAP_SERVERS: str = Field(default="kafka-1:9092")

    # ── AzamPay ───────────────────────────────────────────────────────────────
    AZAMPAY_APP_NAME:       str = Field(default="Riviwa")
    AZAMPAY_CLIENT_ID:      str = Field(default="")
    AZAMPAY_CLIENT_SECRET:  str = Field(default="")
    AZAMPAY_BASE_URL:       str = Field(default="https://authenticator.azampay.co.tz")
    AZAMPAY_CHECKOUT_URL:   str = Field(default="https://checkout.azampay.co.tz")

    # ── Selcom ────────────────────────────────────────────────────────────────
    SELCOM_BASE_URL:        str = Field(default="https://apigw.selcommobile.com/v1")
    SELCOM_API_KEY:         str = Field(default="")
    SELCOM_API_SECRET:      str = Field(default="")
    SELCOM_VENDOR:          str = Field(default="")

    # ── M-Pesa (Vodacom TZ) ───────────────────────────────────────────────────
    MPESA_BASE_URL:         str = Field(default="https://openapi.m-pesa.com")
    MPESA_API_KEY:          str = Field(default="")
    MPESA_PUBLIC_KEY:       str = Field(default="")  # RSA public key for token encryption
    MPESA_SERVICE_PROVIDER_CODE: str = Field(default="")

    # ── Callback ──────────────────────────────────────────────────────────────
    PAYMENT_CALLBACK_BASE_URL: str = Field(
        default="https://api.riviwa.com",
        description="Base URL for payment gateway callbacks. Must be publicly reachable.",
    )

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    @property
    def SYNC_DATABASE_URL(self) -> str:
        """Synchronous URL for Alembic migrations (psycopg v3 driver)."""
        url = self.DATABASE_URL
        url = url.replace("postgresql+asyncpg://", "postgresql+psycopg://")
        url = url.replace("postgresql://", "postgresql+psycopg://")
        return url


settings = Settings()

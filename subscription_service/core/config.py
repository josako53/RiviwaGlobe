"""core/config.py — Settings for subscription_service."""
from __future__ import annotations

from decimal import Decimal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    # ── Database ──────────────────────────────────────────────────────────────
    SUBSCRIPTION_DB_HOST:     str = Field(default="subscription_db")
    SUBSCRIPTION_DB_PORT:     int = Field(default=5432)
    SUBSCRIPTION_DB_USER:     str = Field(default="subscription_admin")
    SUBSCRIPTION_DB_PASSWORD: str = Field(default="subscription_pass")
    SUBSCRIPTION_DB_NAME:     str = Field(default="subscription_db")

    # ── Auth (JWT verification — same secret as auth_service) ─────────────────
    AUTH_SECRET_KEY: str = Field(default="")
    AUTH_ALGORITHM:  str = Field(default="HS256")

    # ── Internal service key ──────────────────────────────────────────────────
    INTERNAL_SERVICE_KEY: str = Field(default="change-me-in-production")

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL: str = Field(default="redis://redis:6379/4")

    # ── Kafka ─────────────────────────────────────────────────────────────────
    KAFKA_BOOTSTRAP_SERVERS: str = Field(default="kafka-1:9092")

    # ── Service URLs ──────────────────────────────────────────────────────────
    AUTH_SERVICE_URL:         str = Field(default="http://riviwa_auth_service:8000")
    NOTIFICATION_SERVICE_URL: str = Field(default="http://notification_service:8060")

    # ── Payment gateways ──────────────────────────────────────────────────────
    # AzamPay
    AZAMPAY_APP_NAME:     str = Field(default="Riviwa")
    AZAMPAY_CLIENT_ID:    str = Field(default="")
    AZAMPAY_CLIENT_SECRET: str = Field(default="")
    AZAMPAY_BASE_URL:     str = Field(default="https://authenticator.azampay.co.tz")
    AZAMPAY_CHECKOUT_URL: str = Field(default="https://checkout.azampay.co.tz")

    # Selcom
    SELCOM_BASE_URL:    str = Field(default="https://apigw.selcommobile.com/v1")
    SELCOM_API_KEY:     str = Field(default="")
    SELCOM_API_SECRET:  str = Field(default="")
    SELCOM_VENDOR:      str = Field(default="")

    # M-Pesa
    MPESA_BASE_URL:              str = Field(default="https://openapi.m-pesa.com")
    MPESA_API_KEY:               str = Field(default="")
    MPESA_PUBLIC_KEY:            str = Field(default="")
    MPESA_SERVICE_PROVIDER_CODE: str = Field(default="")

    # Stripe
    STRIPE_SECRET_KEY:     str = Field(default="")
    STRIPE_WEBHOOK_SECRET: str = Field(default="")

    # ── Callback URL (for mobile money webhooks) ──────────────────────────────
    PAYMENT_CALLBACK_BASE_URL: str = Field(default="https://api.riviwa.com")

    # ── Tax ───────────────────────────────────────────────────────────────────
    TAX_RATE: Decimal = Field(default=Decimal("0.18"))   # 18% VAT

    # ── Runtime ───────────────────────────────────────────────────────────────
    ENVIRONMENT: str = Field(default="production")
    DEBUG:       bool = Field(default=False)

    # ── Computed URLs ─────────────────────────────────────────────────────────
    @property
    def ASYNC_DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.SUBSCRIPTION_DB_USER}:{self.SUBSCRIPTION_DB_PASSWORD}"
            f"@{self.SUBSCRIPTION_DB_HOST}:{self.SUBSCRIPTION_DB_PORT}/{self.SUBSCRIPTION_DB_NAME}"
        )

    @property
    def SYNC_DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg://{self.SUBSCRIPTION_DB_USER}:{self.SUBSCRIPTION_DB_PASSWORD}"
            f"@{self.SUBSCRIPTION_DB_HOST}:{self.SUBSCRIPTION_DB_PORT}/{self.SUBSCRIPTION_DB_NAME}"
        )


settings = Settings()

from __future__ import annotations
import re
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ENVIRONMENT: str = "production"

    # Database
    QR_DB_HOST:     str = "qr_db"
    QR_DB_PORT:     int = 5432
    QR_DB_USER:     str = "qr_admin"
    QR_DB_PASSWORD: str = "qr_pass_444"
    QR_DB_NAME:     str = "qr_db"

    # Auth
    AUTH_SECRET_KEY: str = ""
    AUTH_ALGORITHM:  str = "HS256"

    # Service-to-service
    INTERNAL_SERVICE_KEY: str = "change-me-set-a-real-secret-in-production"
    AUTH_SERVICE_URL:     str = "http://riviwa_auth_service:8000"
    FEEDBACK_SERVICE_URL: str = "http://feedback_service:8090"
    AI_SERVICE_URL:       str = "http://ai_service:8085"

    # MinIO
    MINIO_ENDPOINT:   str = "http://minio:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    QR_BUCKET:        str = "riviwa-qr-codes"

    # QR
    FEEDBACK_APP_URL:   str = "https://app.riviwa.com"
    SHORT_CODE_CHARS:   str = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
    SMS_SHORT_NUMBER:   str = "+255XXXXXXX"

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka-1:9092"
    KAFKA_QR_TOPIC:          str = "riviwa.qr.events"
    KAFKA_FEEDBACK_TOPIC:    str = "riviwa.feedback.events"
    KAFKA_CONSUMER_GROUP:    str = "qr_service_group"

    @property
    def async_db_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.QR_DB_USER}:{self.QR_DB_PASSWORD}"
            f"@{self.QR_DB_HOST}:{self.QR_DB_PORT}/{self.QR_DB_NAME}"
        )

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

from __future__ import annotations
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ENVIRONMENT: str = "production"

    # Database
    VERIFICATION_DB_HOST:     str = "verification_db"
    VERIFICATION_DB_PORT:     int = 5432
    VERIFICATION_DB_NAME:     str = "verification_db"
    VERIFICATION_DB_USER:     str = "verification_admin"
    VERIFICATION_DB_PASSWORD: str = "verification_pass"

    # Auth (JWT verification — same secret as auth service)
    AUTH_SECRET_KEY: str = ""
    AUTH_ALGORITHM:  str = "HS256"

    # Internal service key (X-Service-Key)
    INTERNAL_SERVICE_KEY: str = "change-me-set-a-real-secret-in-production"

    # Service URLs
    QR_SERVICE_URL:      str = "http://qr_service:8120"
    PRODUCT_SERVICE_URL: str = "http://product_service:8110"
    AI_SERVICE_URL:      str = "http://ai_service:8085"

    # MinIO / S3
    MINIO_ENDPOINT:      str = "http://minio:9000"
    MINIO_ACCESS_KEY:    str = "minioadmin"
    MINIO_SECRET_KEY:    str = "minioadmin"
    VERIFICATION_BUCKET: str = "riviwa-verification"

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS:     str = "kafka-1:9092"
    KAFKA_VERIFICATION_TOPIC:    str = "riviwa.verification.events"

    @property
    def async_db_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.VERIFICATION_DB_USER}:{self.VERIFICATION_DB_PASSWORD}"
            f"@{self.VERIFICATION_DB_HOST}:{self.VERIFICATION_DB_PORT}/{self.VERIFICATION_DB_NAME}"
        )

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

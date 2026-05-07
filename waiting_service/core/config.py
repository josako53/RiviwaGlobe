from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    WAITING_DB_HOST:     str = Field(default="waiting_db")
    DB_PORT:             int = Field(default=5432)
    WAITING_DB_USER:     str = Field(default="waiting_admin")
    WAITING_DB_PASSWORD: str = Field(default="waiting_pass_130")
    WAITING_DB_NAME:     str = Field(default="waiting_db")

    SERVICE_NAME: str  = Field(default="waiting_service")
    API_V1_STR:   str  = Field(default="/api/v1")
    ENVIRONMENT:  str  = Field(default="production")
    DEBUG:        bool = Field(default=False)

    KAFKA_BOOTSTRAP_SERVERS: str = Field(default="kafka-1:9092")

    AUTH_SECRET_KEY:      str = Field(default="")
    AUTH_ALGORITHM:       str = Field(default="HS256")
    INTERNAL_SERVICE_KEY: str = Field(default="change-me-in-production")

    REDIS_URL: str = Field(default="redis://redis:6379/9")

    ETA_ALERT_THRESHOLD_MINUTES:    int = Field(default=15)
    SCHEDULER_ETA_INTERVAL_SECONDS: int = Field(default=30)

    @property
    def SYNC_DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg://{self.WAITING_DB_USER}:{self.WAITING_DB_PASSWORD}"
            f"@{self.WAITING_DB_HOST}:{self.DB_PORT}/{self.WAITING_DB_NAME}"
        )

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.WAITING_DB_USER}:{self.WAITING_DB_PASSWORD}"
            f"@{self.WAITING_DB_HOST}:{self.DB_PORT}/{self.WAITING_DB_NAME}"
        )


settings = Settings()

# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  translation_service  |  Port: 8050  |  DB: translation_db (5438)
# FILE     :  core/config.py
# ───────────────────────────────────────────────────────────────────────────
from __future__ import annotations
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    # ── Database ──────────────────────────────────────────────────────────────
    TRANSLATION_DB_HOST:     str = Field(default="translation_db")
    DB_PORT:                 int = Field(default=5432)
    TRANSLATION_DB_USER:     str = Field(default="trans_admin")
    TRANSLATION_DB_PASSWORD: str = Field(default="trans_pass_321")
    TRANSLATION_DB_NAME:     str = Field(default="translation_db")

    @property
    def SYNC_DATABASE_URL(self) -> str:
        """Used by Alembic (synchronous psycopg driver)."""
        return (
            f"postgresql+psycopg://{self.TRANSLATION_DB_USER}:{self.TRANSLATION_DB_PASSWORD}"
            f"@{self.TRANSLATION_DB_HOST}:{self.DB_PORT}/{self.TRANSLATION_DB_NAME}"
        )

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        """Used by FastAPI / SQLAlchemy async engine."""
        return (
            f"postgresql+asyncpg://{self.TRANSLATION_DB_USER}:{self.TRANSLATION_DB_PASSWORD}"
            f"@{self.TRANSLATION_DB_HOST}:{self.DB_PORT}/{self.TRANSLATION_DB_NAME}"
        )

    # ── App ───────────────────────────────────────────────────────────────────
    ENVIRONMENT:  str  = Field(default="production")
    DEBUG:        bool = Field(default=False)
    SERVICE_NAME: str  = Field(default="translation_service")

    # ── Internal service key (shared secret across all services) ──────────────
    INTERNAL_SERVICE_KEY: str = Field(default="change-me-in-env")

    # ── Redis — translation + detection cache ─────────────────────────────────
    REDIS_URL:              str = Field(default="redis://redis:6379/4")
    TRANSLATION_CACHE_TTL:  int = Field(default=86400)   # 24 h
    DETECTION_CACHE_TTL:    int = Field(default=3600)    # 1 h

    # ── Translation provider ─────────────────────────────────────────────────
    # Set TRANSLATION_PROVIDER to "google", "deepl", or "libre"
    TRANSLATION_PROVIDER: str = Field(
        default="google",
        description="Active translation provider: google | deepl | libre",
    )

    # ── Google Cloud Translation API ──────────────────────────────────────────
    GOOGLE_PROJECT_ID:             str = Field(default="")
    GOOGLE_APPLICATION_CREDENTIALS: str = Field(
        default="",
        description="Path to GCP service account JSON or JSON string content.",
    )

    # ── DeepL API ─────────────────────────────────────────────────────────────
    DEEPL_API_KEY:     str  = Field(default="")
    DEEPL_FREE_TIER:   bool = Field(default=True)   # free tier uses api-free.deepl.com

    # ── LibreTranslate (self-hosted fallback) ─────────────────────────────────
    LIBRE_TRANSLATE_URL:     str = Field(default="http://libretranslate:5000")
    LIBRE_TRANSLATE_API_KEY: str = Field(default="")

    # ── NLLB-200 local model ──────────────────────────────────────────────────
    # Set NLLB_ENABLED=true to activate the local NLLB provider.
    # The model is downloaded once to NLLB_MODEL_DIR on first startup.
    # NLLB is used as the LOCAL fallback when all external APIs are unavailable,
    # or as primary for African languages when TRANSLATION_PROVIDER=nllb.
    NLLB_ENABLED:    bool = Field(default=True)
    NLLB_MODEL_NAME: str  = Field(
        default="facebook/nllb-200-distilled-1.3B",
        description=(
            "HuggingFace model ID. Options:\n"
            "  facebook/nllb-200-distilled-600M  — lighter, faster on CPU\n"
            "  facebook/nllb-200-distilled-1.3B  — best quality/speed trade-off\n"
            "  facebook/nllb-200-1.3B            — full quality, highest RAM"
        ),
    )
    NLLB_MODEL_DIR: str = Field(
        default="/models/nllb",
        description="Local directory where the NLLB model weights are stored.",
    )
    NLLB_WORKERS: int = Field(
        default=2,
        description="ThreadPoolExecutor workers for CPU inference.",
    )
    NLLB_MAX_LENGTH: int = Field(
        default=512,
        description="Maximum token length for generated translations.",
    )

    # ── Kafka ─────────────────────────────────────────────────────────────────
    KAFKA_BOOTSTRAP_SERVERS: str = Field(
        default="kafka-1:9092",
        description="Comma-separated Kafka broker addresses.",
    )

    # ── Default / fallback language ───────────────────────────────────────────
    DEFAULT_LANGUAGE:  str = Field(default="sw")    # Kiswahili — Tanzania primary
    FALLBACK_LANGUAGE: str = Field(default="en")    # English fallback

    # ── Detection confidence threshold ────────────────────────────────────────
    # Text below this confidence is treated as the user's current preferred language.
    MIN_DETECTION_CONFIDENCE: float = Field(default=0.80)

    # ── Minimum text length for reliable detection ────────────────────────────
    MIN_DETECT_CHARS: int = Field(default=20)

    @property
    def is_staging(self) -> bool:
        return self.ENVIRONMENT in ("staging", "development")


settings = Settings()

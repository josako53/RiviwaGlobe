# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  feedback_service     |  Port: 8090  |  DB: feedback_db (5434)
# FILE     :  core/config.py
# ───────────────────────────────────────────────────────────────────────────
# core/config.py
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    # ── Database ──────────────────────────────────────────────────────────────
    FEEDBACK_DB_HOST:     str = Field(default="feedback_db")
    DB_PORT:              int = Field(default=5432)
    FEEDBACK_DB_USER:     str = Field(default="feedback_admin")
    FEEDBACK_DB_PASSWORD: str = Field(default="feedback_pass_456")
    FEEDBACK_DB_NAME:     str = Field(default="feedback_db")

    # ── App ───────────────────────────────────────────────────────────────────
    API_V1_STR:              str  = "/api/v1"
    FEEDBACK_SERVICE_NAME:   str  = Field(default="feedback_service")
    APP_BASE_URL:            str  = Field(default="https://riviwa.com")

    # ── Kafka ─────────────────────────────────────────────────────────────────
    KAFKA_BOOTSTRAP_SERVERS: str = Field(default="kafka-1:9092")

    # ── JWT — validates tokens from auth_service ───────────────────────────────
    AUTH_SECRET_KEY: str = Field(
        default="8f3d951a56fa9820abee2a70d9d44acfbe7965ef8562fd40b489c8759bfa2cfe",
    )
    AUTH_ALGORITHM: str = Field(default="HS256")

    # ── Runtime ───────────────────────────────────────────────────────────────
    ENVIRONMENT: str  = Field(default="production")
    DEBUG:       bool = Field(default=False)

    # ── Cross-service communication ───────────────────────────────────────────
    # auth_service base URL — used by channels.py to call channel-register
    AUTH_SERVICE_URL: str = Field(
        default="http://riviwa_auth_service:8000",
        description="Base URL of auth_service for internal service calls.",
    )
    # Shared secret sent as X-Service-Key header on internal calls
    INTERNAL_SERVICE_KEY: str = Field(
        default="change-me-in-production",
        description=(
            "Service-to-service auth key. Must match auth_service INTERNAL_SERVICE_KEY. "
            "Set in .env — never commit the real value."
        ),
    )

    # ── LLM / AI conversation engine ─────────────────────────────────────────
    ANTHROPIC_API_KEY:  str  = Field(default="",
                                      description="Anthropic API key for Claude LLM (AI conversation engine).")

    # ── Voice / Audio pipeline ────────────────────────────────────────────────
    # STT (Speech-to-Text)
    STT_PROVIDER_ORDER:     str  = Field(default="whisper,google_stt",
                                         description="Comma-separated STT provider priority list.")
    WHISPER_MODE:           str  = Field(default="api",
                                         description="'api' (OpenAI) or 'local' (faster-whisper).")
    WHISPER_MODEL_SIZE:     str  = Field(default="medium",
                                         description="faster-whisper model size when WHISPER_MODE=local.")
    OPENAI_API_KEY:         str  = Field(default="",
                                         description="OpenAI API key for Whisper API mode.")
    GOOGLE_STT_API_KEY:     str  = Field(default="",
                                         description="Google Cloud STT API key.")
    AZURE_STT_KEY:          str  = Field(default="",
                                         description="Azure Cognitive Services STT key.")
    AZURE_STT_REGION:       str  = Field(default="eastus")

    # TTS (Text-to-Speech) — for PHONE_CALL and app voice replies
    TTS_PROVIDER:           str  = Field(default="google_tts",
                                         description="'google_tts' | 'azure_tts' | 'elevenlabs'.")
    GOOGLE_TTS_API_KEY:     str  = Field(default="")
    AZURE_TTS_KEY:          str  = Field(default="")
    AZURE_TTS_REGION:       str  = Field(default="eastus")
    ELEVENLABS_API_KEY:     str  = Field(default="")
    ELEVENLABS_DEFAULT_VOICE_ID: str = Field(default="21m00Tcm4TlvDq8ikWAM",
                                             description="ElevenLabs voice ID for the default Riviwa voice.")

    # Object storage (MinIO / S3)
    STORAGE_PROVIDER:       str  = Field(default="minio",
                                         description="'minio' | 's3' | 'local'.")
    MINIO_ENDPOINT:         str  = Field(default="http://minio:9000")
    MINIO_ACCESS_KEY:       str  = Field(default="minioadmin")
    MINIO_SECRET_KEY:       str  = Field(default="minioadmin")
    VOICE_STORAGE_BUCKET:   str  = Field(default="riviwa-voice",
                                         description="Object storage bucket for audio files.")
    LOCAL_STORAGE_PATH:     str  = Field(default="/tmp/riviwa-voice",
                                         description="Local path for STORAGE_PROVIDER=local (testing only).")

    # WhatsApp voice
    WHATSAPP_ACCESS_TOKEN:  str  = Field(default="",
                                         description="Meta WhatsApp Business API access token.")
    WHATSAPP_API_VERSION:   str  = Field(default="v18.0")
    WHATSAPP_VERIFY_TOKEN:  str  = Field(default="riviwa_webhook_verify",
                                         description="Secret token for Meta webhook URL verification.")

    @property
    def SYNC_DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg://{self.FEEDBACK_DB_USER}:{self.FEEDBACK_DB_PASSWORD}"
            f"@{self.FEEDBACK_DB_HOST}:{self.DB_PORT}/{self.FEEDBACK_DB_NAME}"
        )

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.FEEDBACK_DB_USER}:{self.FEEDBACK_DB_PASSWORD}"
            f"@{self.FEEDBACK_DB_HOST}:{self.DB_PORT}/{self.FEEDBACK_DB_NAME}"
        )


settings = Settings()

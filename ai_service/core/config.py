# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  ai_service     |  Port: 8085  |  DB: ai_db (5440)
# FILE     :  core/config.py
# ───────────────────────────────────────────────────────────────────────────
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    # ── Database ──────────────────────────────────────────────────────────────
    AI_DB_HOST:     str = Field(default="ai_db")
    DB_PORT:        int = Field(default=5432)
    AI_DB_USER:     str = Field(default="ai_admin")
    AI_DB_PASSWORD: str = Field(default="ai_pass_789")
    AI_DB_NAME:     str = Field(default="ai_db")

    # ── App ───────────────────────────────────────────────────────────────────
    API_V1_STR:        str = "/api/v1"
    AI_SERVICE_NAME:   str = Field(default="ai_service")
    APP_BASE_URL:      str = Field(default="https://riviwa.com")
    ENVIRONMENT:       str = Field(default="production")
    DEBUG:            bool = Field(default=False)

    # ── Kafka ─────────────────────────────────────────────────────────────────
    KAFKA_BOOTSTRAP_SERVERS: str = Field(default="kafka-1:9092")

    # ── JWT — validates tokens from auth_service ───────────────────────────────
    AUTH_SECRET_KEY: str = Field(
        default="8f3d951a56fa9820abee2a70d9d44acfbe7965ef8562fd40b489c8759bfa2cfe"
    )
    AUTH_ALGORITHM: str = Field(default="HS256")

    # ── Service-to-service ────────────────────────────────────────────────────
    INTERNAL_SERVICE_KEY:  str = Field(default="change-me-in-production")
    FEEDBACK_SERVICE_URL:  str = Field(default="http://feedback_service:8090")
    AUTH_SERVICE_URL:      str = Field(default="http://riviwa_auth_service:8000")
    STAKEHOLDER_SERVICE_URL: str = Field(default="http://stakeholder_service:8070")

    # ── Ollama LLM ────────────────────────────────────────────────────────────
    OLLAMA_BASE_URL:     str = Field(default="http://ollama:11434")
    OLLAMA_MODEL:        str = Field(default="llama3.2:3b",
                                     description="Ollama model for conversation (e.g. llama3.2:3b, mistral:7b)")
    OLLAMA_TIMEOUT_SECS: int = Field(default=60)

    # ── Qdrant vector store ───────────────────────────────────────────────────
    QDRANT_HOST: str = Field(default="qdrant")
    QDRANT_PORT: int = Field(default=6333)

    # ── Embedding model ───────────────────────────────────────────────────────
    EMBEDDING_MODEL: str = Field(default="all-MiniLM-L6-v2")
    EMBEDDING_MODEL_PATH: str = Field(default="/models/sentence-transformers")
    QDRANT_COLLECTION_PROJECTS: str = Field(default="ai_projects")
    QDRANT_COLLECTION_FEEDBACK: str = Field(default="ai_feedback_kb")

    # ── Conversation settings ─────────────────────────────────────────────────
    AUTO_SUBMIT_CONFIDENCE: float = Field(default=0.82,
                                          description="Confidence threshold for auto-submitting feedback")
    MAX_TURNS_BEFORE_TIMEOUT: int = Field(default=30)
    SESSION_TIMEOUT_MINUTES: int = Field(default=60)

    # ── WhatsApp ──────────────────────────────────────────────────────────────
    WHATSAPP_ACCESS_TOKEN:  str = Field(default="")
    WHATSAPP_API_VERSION:   str = Field(default="v18.0")
    WHATSAPP_PHONE_NUMBER_ID: str = Field(default="",
                                           description="Meta WhatsApp Business phone number ID for sending messages")
    WHATSAPP_VERIFY_TOKEN:  str = Field(default="riviwa_ai_webhook_verify")

    # ── Groq LLM API (optional — replaces local Ollama for chat if key is set) ──
    GROQ_API_KEY:  str = Field(default="", description="Groq API key — if set, routes chat through Groq instead of local Ollama")
    GROQ_MODEL:    str = Field(default="llama-3.3-70b-versatile", description="Groq model name")
    GROQ_BASE_URL: str = Field(default="https://api.groq.com/openai/v1")

    # ── STT (Speech-to-Text for voice notes) ─────────────────────────────────
    OPENAI_API_KEY: str = Field(default="", description="OpenAI Whisper API key")
    GOOGLE_STT_API_KEY: str = Field(default="")

    # ── Object storage (voice note downloads from WhatsApp) ───────────────────
    MINIO_ENDPOINT:   str = Field(default="http://minio:9000")
    MINIO_ACCESS_KEY: str = Field(default="minioadmin")
    MINIO_SECRET_KEY: str = Field(default="minioadmin")

    @property
    def SYNC_DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg://{self.AI_DB_USER}:{self.AI_DB_PASSWORD}"
            f"@{self.AI_DB_HOST}:{self.DB_PORT}/{self.AI_DB_NAME}"
        )

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.AI_DB_USER}:{self.AI_DB_PASSWORD}"
            f"@{self.AI_DB_HOST}:{self.DB_PORT}/{self.AI_DB_NAME}"
        )


settings = Settings()

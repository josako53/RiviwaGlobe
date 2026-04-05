# core/config.py
# All environment variables: DB · Redis · Kafka · JWT · OTP · lockout · OAuth providers

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    # ── Database ──────────────────────────────────────────────────────────────
    AUTH_DB_HOST:     str = Field(default="riviwa_auth_db")
    DB_PORT:          int = Field(default=5432)
    AUTH_DB_USER:     str = Field(default="riviwa_auth_admin")
    AUTH_DB_PASSWORD: str = Field(default="auth_pass_123")
    AUTH_DB_NAME:     str = Field(default="auth_db")

    # ── JWT / Token security ───────────────────────────────────────────────────
    SECRET_KEY: str = Field(
        default="8f3d951a56fa9820abee2a70d9d44acfbe7965ef8562fd40b489c8759bfa2cfe",
        description="HMAC secret used to sign JWT access tokens (HS256). "
                    "Rotate this in production via environment variable.",
    )
    ALGORITHM: str = Field(
        default="HS256",
        description="JWT signing algorithm. HS256 for symmetric, RS256 for asymmetric.",
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,
        description="Access token lifetime in minutes. "
                    "expires_in (seconds) = ACCESS_TOKEN_EXPIRE_MINUTES × 60.",
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7,
        description="Refresh token lifetime in days. "
                    "Stored as an opaque UUID in Redis. Rotated on every use.",
    )

    # ── OTP configuration ─────────────────────────────────────────────────────
    OTP_REGISTRATION_TTL_SECONDS: int = Field(
        default=600,        # 10 minutes
        description="Lifetime of a registration OTP / registration_token in Redis.",
    )
    OTP_LOGIN_TTL_SECONDS: int = Field(
        default=300,        # 5 minutes
        description="Lifetime of a login OTP / login_token in Redis.",
    )
    OTP_PASSWORD_RESET_TTL_SECONDS: int = Field(
        default=600,        # 10 minutes
        description="Lifetime of a password-reset OTP / reset_token in Redis.",
    )
    OTP_STANDALONE_TTL_SECONDS: int = Field(
        default=600,        # 10 minutes
        description="Lifetime of a standalone OTP (phone_verify, email_verify) in Redis.",
    )
    OTP_MAX_ATTEMPTS: int = Field(
        default=5,
        description="Maximum wrong OTP submissions before the session is destroyed "
                    "and the user must restart the flow.",
    )
    OTP_RESEND_LIMIT: int = Field(
        default=3,
        description="Maximum number of times an OTP can be resent within a single "
                    "registration or login session.",
    )
    OTP_LENGTH: int = Field(
        default=6,
        description="Number of digits in a generated OTP code.",
    )

    # ── Login lockout ──────────────────────────────────────────────────────────
    MAX_LOGIN_ATTEMPTS: int = Field(
        default=5,
        description="Failed password attempts (Step 1) before the account is "
                    "temporarily locked. Counter resets on successful OTP verification.",
    )
    LOCKOUT_DURATION_MINUTES: int = Field(
        default=30,
        description="Duration of the account lockout after MAX_LOGIN_ATTEMPTS "
                    "consecutive failures. Stored in User.locked_until.",
    )

    # ── App ───────────────────────────────────────────────────────────────────
    API_V1_STR:                 str  = "/api/v1"
    RIVIWA_AUTH_SERVICE_NAME:   str  = Field(default="riviwa_auth_service")
    APP_BASE_URL:               str  = Field(
        default="https://riviwa.com",
        description="Used for building redirect URLs in ID verification sessions "
                    "and OAuth callbacks.",
    )
    TRUST_PROXY: bool = Field(
        default=False,
        description="Set True when running behind nginx / a load balancer so that "
                    "X-Forwarded-For is trusted for IP extraction.",
    )

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL. "
                    "Used for: OTP sessions · refresh-token store · "
                    "JWT deny-list · rate limiting · geo cache.",
    )

    # ── Kafka ─────────────────────────────────────────────────────────────────
    KAFKA_BOOTSTRAP_SERVERS: str = Field(
        default="kafka-1:9092,kafka-2:9092,kafka-3:9092,kafka-4:9092",
    )

    # ── Celery ────────────────────────────────────────────────────────────────
    CELERY_BROKER_URL: str = Field(
        default="redis://localhost:6379/1",
        description="Celery broker. Redis recommended for development; "
                    "use a dedicated Redis DB or RabbitMQ in production.",
    )
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/2")

    # ── OAuth providers ───────────────────────────────────────────────────────
    # Google OAuth 2.0 / Sign In with Google
    GOOGLE_CLIENT_ID: str = Field(
        default="",
        description="Google OAuth 2.0 client ID. "
                    "Used to verify id_token audience claim.",
    )
    GOOGLE_CLIENT_SECRET: str = Field(
        default="",
        description="Google OAuth 2.0 client secret (server-side flows only).",
    )

    # Apple Sign In
    APPLE_CLIENT_ID: str = Field(
        default="",
        description="Apple Services ID (bundle ID). "
                    "Used as the audience when verifying Apple identity tokens.",
    )
    APPLE_TEAM_ID:   str = Field(default="", description="Apple Developer Team ID.")
    APPLE_KEY_ID:    str = Field(default="", description="Apple Sign-In private key ID.")
    APPLE_PRIVATE_KEY: str = Field(
        default="",
        description="PEM-encoded Apple Sign-In private key (.p8 file contents). "
                    "Set via environment variable — never commit to source control.",
    )

    # Facebook Login
    FACEBOOK_APP_ID:     str = Field(default="", description="Facebook App ID.")
    FACEBOOK_APP_SECRET: str = Field(
        default="",
        description="Facebook App Secret. Used to verify access tokens via "
                    "the graph.facebook.com/debug_token endpoint.",
    )

    # ── ID Verification Provider ───────────────────────────────────────────────
    ID_VERIFICATION_PROVIDER: str = Field(
        default="stub",
        description="stub | stripe | onfido | jumio",
    )

    # Stripe Identity
    STRIPE_SECRET_KEY:      str = Field(default="")
    STRIPE_WEBHOOK_SECRET:  str = Field(default="")

    # Onfido
    ONFIDO_API_TOKEN:    str = Field(default="")
    ONFIDO_WEBHOOK_TOKEN: str = Field(default="")
    ONFIDO_WORKFLOW_ID:  str = Field(default="")

    # ── OTP notification providers ─────────────────────────────────────────────
    # Controls which backend delivers SMS and email OTPs.
    #
    # OTP_SMS_PROVIDER:
    #   "twilio_verify"  RECOMMENDED — Twilio generates, sends, and verifies.
    #                    No OTP hash stored. Twilio handles TTL and retries.
    #   "twilio_sms"     We generate the code, Twilio sends the SMS.
    #                    OTP hash stored in Redis (our existing pattern).
    #   "stub"           Development / CI — logs the code, no external calls.
    #
    # OTP_EMAIL_PROVIDER:
    #   "smtp"           SMTP delivery (Gmail, SendGrid, Mailgun, etc.)
    #   "stub"           Development / CI.

    OTP_SMS_PROVIDER: str = Field(
        default="stub",
        description="SMS OTP provider. twilio_verify (recommended) | twilio_sms | stub",
    )
    OTP_EMAIL_PROVIDER: str = Field(
        default="stub",
        description="Email OTP provider. smtp | stub",
    )

    # ── Twilio credentials ─────────────────────────────────────────────────────
    # CRITICAL: Always set via environment variables. Never hardcode.
    # Rotate immediately if accidentally exposed.

    TWILIO_ACCOUNT_SID: str = Field(
        default="",
        description="Twilio Account SID. Starts with 'AC'. "
                    "Found in the Twilio Console dashboard.",
    )
    TWILIO_AUTH_TOKEN: str = Field(
        default="",
        description="Twilio Auth Token. Treat as a password — never commit to source control.",
    )
    TWILIO_VERIFY_SERVICE_SID: str = Field(
        default="",
        description="Twilio Verify Service SID. Starts with 'VA'. "
                    "Create at: console.twilio.com/verify/services",
    )
    TWILIO_FROM_NUMBER: str = Field(
        default="",
        description="E.164 Twilio number for Programmable SMS e.g. '+12345678900'. "
                    "Only needed for twilio_sms provider.",
    )

    # ── SMTP email settings (OTP_EMAIL_PROVIDER = "smtp") ─────────────────────
    SMTP_HOST: str = Field(
        default="localhost",
        description="SMTP server hostname. e.g. 'smtp.gmail.com', 'smtp.sendgrid.net'",
    )
    SMTP_PORT: int = Field(
        default=587,
        description="SMTP port. 587 for STARTTLS (recommended), 465 for SSL.",
    )
    SMTP_USER: str = Field(
        default="",
        description="SMTP username. For Gmail: your address. For SendGrid: 'apikey'.",
    )
    SMTP_PASSWORD: str = Field(
        default="",
        description="SMTP password or API key. For Gmail: use an App Password.",
    )
    SMTP_USE_TLS: bool = Field(
        default=True,
        description="True = STARTTLS on port 587. False = SSL on port 465.",
    )
    EMAIL_FROM_ADDRESS: str = Field(
        default="noreply@riviwa.com",
        description="Sender address shown to recipients. "
                    "Format: 'Display Name <address@domain.com>' or 'address@domain.com'.",
    )

    # ── Runtime environment ────────────────────────────────────────────────────
    ENVIRONMENT: str = Field(
        default="production",
        description="production | staging | development | test",
    )
    DEBUG: bool = Field(
        default=False,
        description="When True, raw OTP codes appear in logs (stub + twilio_sms only). "
                    "NEVER set True in production.",
    )

    # ── Cross-service communication ────────────────────────────────────────────
    # Shared secret verified by _require_service_key in channel_auth.py.
    # feedback_service sends this as X-Service-Key on every channel-register call.
    INTERNAL_SERVICE_KEY: str = Field(
        default="change-me-in-production",
        description=(
            "Service-to-service auth key for internal endpoints. "
            "Must match feedback_service INTERNAL_SERVICE_KEY. Set in .env."
        ),
    )
    ADMIN_EMAIL:      str = Field(default="admin@yourapp.com")
    ADMIN_PASSWORD:   str = Field(default="Change_me_immediately_123!")
    ADMIN_FIRST_NAME: str = Field(default="Admin")
    ADMIN_LAST_NAME:  str = Field(default="User")

    # ── Fraud ────────────────────────────────────────────────────────────
    FRAUD_SCORE_WARN_THRESHOLD: int = 30
    FRAUD_SCORE_REVIEW_THRESHOLD: int = 50
    FRAUD_SCORE_BLOCK_THRESHOLD: int = 80

    # ── Computed DB URLs ──────────────────────────────────────────────────────
    @property
    def SYNC_DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg://{self.AUTH_DB_USER}:{self.AUTH_DB_PASSWORD}"
            f"@{self.AUTH_DB_HOST}:{self.DB_PORT}/{self.AUTH_DB_NAME}"
        )

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.AUTH_DB_USER}:{self.AUTH_DB_PASSWORD}"
            f"@{self.AUTH_DB_HOST}:{self.DB_PORT}/{self.AUTH_DB_NAME}"
        )


settings = Settings()

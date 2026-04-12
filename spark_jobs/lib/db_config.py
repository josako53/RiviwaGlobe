import os
import redis

# ---------------------------------------------------------------------------
# PostgreSQL connection details
# ---------------------------------------------------------------------------

FEEDBACK_DB_HOST = os.getenv("FEEDBACK_DB_HOST", "feedback_db")
FEEDBACK_DB_PORT = os.getenv("FEEDBACK_DB_PORT", "5432")
FEEDBACK_DB_NAME = os.getenv("FEEDBACK_DB_NAME", "feedback_db")
FEEDBACK_DB_USER = os.getenv("FEEDBACK_DB_USER", "postgres")
FEEDBACK_DB_PASSWORD = os.getenv("FEEDBACK_DB_PASSWORD", "postgres")

ANALYTICS_DB_HOST = os.getenv("ANALYTICS_DB_HOST", "analytics_db")
ANALYTICS_DB_PORT = os.getenv("ANALYTICS_DB_PORT", "5441")
ANALYTICS_DB_NAME = os.getenv("ANALYTICS_DB_NAME", "analytics_db")
ANALYTICS_DB_USER = os.getenv("ANALYTICS_DB_USER", "postgres")
ANALYTICS_DB_PASSWORD = os.getenv("ANALYTICS_DB_PASSWORD", "postgres")

# ---------------------------------------------------------------------------
# JDBC URLs
# ---------------------------------------------------------------------------

FEEDBACK_JDBC_URL = (
    f"jdbc:postgresql://{FEEDBACK_DB_HOST}:{FEEDBACK_DB_PORT}/{FEEDBACK_DB_NAME}"
)

ANALYTICS_JDBC_URL = (
    f"jdbc:postgresql://{ANALYTICS_DB_HOST}:{ANALYTICS_DB_PORT}/{ANALYTICS_DB_NAME}"
)

# ---------------------------------------------------------------------------
# JDBC option dicts (pass directly to .option(**k, v) or spark.read.jdbc)
# ---------------------------------------------------------------------------

FEEDBACK_JDBC_PROPS = {
    "user": FEEDBACK_DB_USER,
    "password": FEEDBACK_DB_PASSWORD,
    "driver": "org.postgresql.Driver",
}

ANALYTICS_JDBC_PROPS = {
    "user": ANALYTICS_DB_USER,
    "password": ANALYTICS_DB_PASSWORD,
    "driver": "org.postgresql.Driver",
}


def get_feedback_jdbc_options() -> dict:
    """Return options dict for spark.read.format('jdbc')."""
    return {
        "url": FEEDBACK_JDBC_URL,
        "user": FEEDBACK_DB_USER,
        "password": FEEDBACK_DB_PASSWORD,
        "driver": "org.postgresql.Driver",
    }


def get_analytics_jdbc_options() -> dict:
    """Return options dict for spark.read.format('jdbc')."""
    return {
        "url": ANALYTICS_JDBC_URL,
        "user": ANALYTICS_DB_USER,
        "password": ANALYTICS_DB_PASSWORD,
        "driver": "org.postgresql.Driver",
    }


# ---------------------------------------------------------------------------
# Redis
# ---------------------------------------------------------------------------

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_SPARK_DB", "6"))


def get_redis_client() -> redis.Redis:
    """Return a synchronous Redis client connected to DB 6 (Spark jobs)."""
    return redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
        retry_on_timeout=True,
    )

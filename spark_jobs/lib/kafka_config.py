import os

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka-1:9092")

# ---------------------------------------------------------------------------
# Topic names
# ---------------------------------------------------------------------------

TOPIC_FEEDBACK_EVENTS = "riviwa.feedback.events"
TOPIC_ORGANISATION_EVENTS = "riviwa.organisation.events"
TOPIC_STAKEHOLDER_EVENTS = "riviwa.stakeholder.events"
TOPIC_AUTH_EVENTS = "riviwa.auth.events"

# ---------------------------------------------------------------------------
# SLA targets (hours)
# ---------------------------------------------------------------------------

ACK_SLA_HOURS: dict[str, int] = {
    "critical": 4,
    "high": 8,
    "medium": 24,
    "low": 48,
}

RES_SLA_HOURS: dict[str, int] = {
    "critical": 72,
    "high": 168,
    "medium": 336,
    "low": 720,
}


def kafka_read_options(
    topic: str,
    starting_offsets: str = "latest",
    max_offsets_per_trigger: int = 10_000,
    fail_on_data_loss: bool = False,
) -> dict:
    """
    Return a dict of Kafka source options for Spark Structured Streaming.

    Usage::

        df = (
            spark.readStream
            .format("kafka")
            .options(**kafka_read_options("my.topic"))
            .load()
        )
    """
    return {
        "kafka.bootstrap.servers": KAFKA_BOOTSTRAP,
        "subscribe": topic,
        "startingOffsets": starting_offsets,
        "maxOffsetsPerTrigger": str(max_offsets_per_trigger),
        "failOnDataLoss": str(fail_on_data_loss).lower(),
        # Security – override via env if needed
        "kafka.security.protocol": os.getenv("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT"),
    }


def kafka_batch_read_options(
    topic: str,
    starting_offsets: str = "earliest",
    ending_offsets: str = "latest",
) -> dict:
    """
    Return options for a batch Kafka read (spark.read.format('kafka')).
    Useful for reading the last N hours in batch jobs.
    """
    return {
        "kafka.bootstrap.servers": KAFKA_BOOTSTRAP,
        "subscribe": topic,
        "startingOffsets": starting_offsets,
        "endingOffsets": ending_offsets,
        "failOnDataLoss": "false",
        "kafka.security.protocol": os.getenv("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT"),
    }

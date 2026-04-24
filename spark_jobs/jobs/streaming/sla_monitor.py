"""
SLA Monitor – PySpark Structured Streaming job.

Reads `riviwa.feedback.events` from Kafka, tracks ACK and resolution SLA
deadlines using flatMapGroupsWithState, and writes breached/met records to
analytics_db.feedback_sla_status.  Live breach flags are also stored in
Redis with a 24-hour TTL.

State schema per feedback_id
-----------------------------
feedback_id          str
project_id           str
priority             str   (critical / high / medium / low)
submitted_at         float (unix epoch seconds)
ack_deadline         float
res_deadline         float
acknowledged_at      float | None
resolved_at          float | None
ack_sla_breached     bool
ack_sla_met          bool
res_sla_breached     bool
res_sla_met          bool
last_event_ts        float
"""
from __future__ import annotations

import sys
import os
import json
import logging
from datetime import datetime, timezone
from typing import Iterator, Tuple

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType,
    StructField,
    StringType,
    DoubleType,
    BooleanType,
    TimestampType,
    LongType,
)
from pyspark.sql.streaming.state import GroupState, GroupStateTimeout

# Make sure the lib package is importable when spark-submit runs /app/jobs/…
sys.path.insert(0, "/app")

from lib.spark_factory import create_spark_session
from lib.db_config import ANALYTICS_JDBC_URL, ANALYTICS_JDBC_PROPS, get_redis_client
from lib.kafka_config import kafka_read_options, TOPIC_FEEDBACK_EVENTS, ACK_SLA_HOURS, RES_SLA_HOURS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sla_monitor")

# ---------------------------------------------------------------------------
# Schema of the JSON payload inside each Kafka message value
# ---------------------------------------------------------------------------

EVENT_SCHEMA = StructType(
    [
        StructField("feedback_id", StringType(), True),
        StructField("project_id", StringType(), True),
        StructField("feedback_type", StringType(), True),
        StructField("priority", StringType(), True),
        StructField("category", StringType(), True),
        StructField("event_type", StringType(), True),
        StructField("submitted_at", StringType(), True),
        StructField("acknowledged_at", StringType(), True),
        StructField("resolved_at", StringType(), True),
        StructField("target_resolution_date", StringType(), True),
    ]
)

# Schema of a single output row written to analytics_db
OUTPUT_SCHEMA = StructType(
    [
        StructField("feedback_id", StringType(), False),
        StructField("project_id", StringType(), True),
        StructField("priority", StringType(), True),
        StructField("submitted_at", TimestampType(), True),
        StructField("ack_deadline", TimestampType(), True),
        StructField("res_deadline", TimestampType(), True),
        StructField("acknowledged_at", TimestampType(), True),
        StructField("resolved_at", TimestampType(), True),
        StructField("ack_sla_met", BooleanType(), True),
        StructField("ack_sla_breached", BooleanType(), True),
        StructField("res_sla_met", BooleanType(), True),
        StructField("res_sla_breached", BooleanType(), True),
        StructField("updated_at", TimestampType(), True),
    ]
)

# Internal state schema (stored as a single-column struct)
STATE_SCHEMA = StructType(
    [
        StructField("feedback_id", StringType(), True),
        StructField("project_id", StringType(), True),
        StructField("priority", StringType(), True),
        StructField("submitted_at", DoubleType(), True),
        StructField("ack_deadline", DoubleType(), True),
        StructField("res_deadline", DoubleType(), True),
        StructField("acknowledged_at", DoubleType(), True),
        StructField("resolved_at", DoubleType(), True),
        StructField("ack_sla_breached", BooleanType(), True),
        StructField("ack_sla_met", BooleanType(), True),
        StructField("res_sla_breached", BooleanType(), True),
        StructField("res_sla_met", BooleanType(), True),
        StructField("last_event_ts", DoubleType(), True),
    ]
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _parse_ts(ts_str) -> float | None:
    """Parse an ISO-8601 or epoch string into a Unix timestamp (float)."""
    if not ts_str:
        return None
    try:
        return float(ts_str)
    except (ValueError, TypeError):
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(ts_str, fmt).replace(tzinfo=timezone.utc)
            return dt.timestamp()
        except ValueError:
            continue
    return None


def _epoch_to_ts(epoch: float | None) -> datetime | None:
    if epoch is None:
        return None
    return datetime.fromtimestamp(epoch, tz=timezone.utc)


# ---------------------------------------------------------------------------
# State function
# ---------------------------------------------------------------------------

def update_sla_state(
    key: Tuple[str],
    events,
    state: GroupState,
) -> Iterator[dict]:
    """
    Called once per group (feedback_id) per micro-batch.
    Returns rows to write to the sink (only when SLA status changes).
    """
    now_epoch = datetime.now(timezone.utc).timestamp()

    # Load or initialise state
    if state.exists:
        s = state.get
    else:
        s = {
            "feedback_id": None,
            "project_id": None,
            "priority": "medium",
            "submitted_at": None,
            "ack_deadline": None,
            "res_deadline": None,
            "acknowledged_at": None,
            "resolved_at": None,
            "ack_sla_breached": False,
            "ack_sla_met": False,
            "res_sla_breached": False,
            "res_sla_met": False,
            "last_event_ts": now_epoch,
        }

    changed = False

    for row in events:
        event_type = row.event_type or ""
        priority = (row.priority or "medium").lower()
        if priority not in ACK_SLA_HOURS:
            priority = "medium"

        submitted_ts = _parse_ts(row.submitted_at)
        acknowledged_ts = _parse_ts(row.acknowledged_at)
        resolved_ts = _parse_ts(row.resolved_at)

        if event_type == "feedback.submitted" and submitted_ts is not None:
            s["feedback_id"] = row.feedback_id
            s["project_id"] = row.project_id
            s["priority"] = priority
            s["submitted_at"] = submitted_ts
            s["ack_deadline"] = submitted_ts + ACK_SLA_HOURS[priority] * 3600
            s["res_deadline"] = submitted_ts + RES_SLA_HOURS[priority] * 3600
            s["last_event_ts"] = submitted_ts
            changed = True

        elif event_type == "feedback.acknowledged" and acknowledged_ts is not None:
            s["acknowledged_at"] = acknowledged_ts
            if s["ack_deadline"] is not None:
                if acknowledged_ts <= s["ack_deadline"]:
                    s["ack_sla_met"] = True
                    s["ack_sla_breached"] = False
                else:
                    s["ack_sla_met"] = False
                    s["ack_sla_breached"] = True
            s["last_event_ts"] = acknowledged_ts
            changed = True

        elif event_type == "feedback.resolved" and resolved_ts is not None:
            s["resolved_at"] = resolved_ts
            if s["res_deadline"] is not None:
                if resolved_ts <= s["res_deadline"]:
                    s["res_sla_met"] = True
                    s["res_sla_breached"] = False
                else:
                    s["res_sla_met"] = False
                    s["res_sla_breached"] = True
            s["last_event_ts"] = resolved_ts
            changed = True

    # Watermark-based timeout check: ACK deadline passed with no acknowledgement
    if state.hasTimedOut:
        if (
            s["submitted_at"] is not None
            and s["acknowledged_at"] is None
            and not s["ack_sla_breached"]
        ):
            s["ack_sla_breached"] = True
            s["ack_sla_met"] = False
            changed = True

    # Update state and register next timeout at ack_deadline
    if not (s["ack_sla_met"] or s["ack_sla_breached"]) and s["ack_deadline"] is not None:
        # Register event-time timeout at ack_deadline
        state.setTimeoutTimestamp(int(s["ack_deadline"] * 1000))
    else:
        # No more timeouts needed for this key once ack is settled
        state.remove()

    state.update(s)

    if changed and s["feedback_id"] is not None:
        yield {
            "feedback_id": s["feedback_id"],
            "project_id": s["project_id"],
            "priority": s["priority"],
            "submitted_at": _epoch_to_ts(s["submitted_at"]),
            "ack_deadline": _epoch_to_ts(s["ack_deadline"]),
            "res_deadline": _epoch_to_ts(s["res_deadline"]),
            "acknowledged_at": _epoch_to_ts(s["acknowledged_at"]),
            "resolved_at": _epoch_to_ts(s["resolved_at"]),
            "ack_sla_met": s["ack_sla_met"],
            "ack_sla_breached": s["ack_sla_breached"],
            "res_sla_met": s["res_sla_met"],
            "res_sla_breached": s["res_sla_breached"],
            "updated_at": datetime.now(timezone.utc),
        }


# ---------------------------------------------------------------------------
# foreachBatch writer
# ---------------------------------------------------------------------------

def write_sla_batch(batch_df, batch_id: int) -> None:
    """Write SLA rows to analytics_db and set Redis keys for breaches."""
    if batch_df.isEmpty():
        return

    try:
        (
            batch_df.write.format("jdbc")
            .option("url", ANALYTICS_JDBC_URL)
            .option("dbtable", "feedback_sla_status")
            .option("user", ANALYTICS_JDBC_PROPS["user"])
            .option("password", ANALYTICS_JDBC_PROPS["password"])
            .option("driver", ANALYTICS_JDBC_PROPS["driver"])
            # Use INSERT … ON CONFLICT UPDATE via PostgreSQL upsert mode
            .option(
                "insertClause",
                "ON CONFLICT (feedback_id) DO UPDATE SET "
                "ack_sla_met=EXCLUDED.ack_sla_met, "
                "ack_sla_breached=EXCLUDED.ack_sla_breached, "
                "res_sla_met=EXCLUDED.res_sla_met, "
                "res_sla_breached=EXCLUDED.res_sla_breached, "
                "acknowledged_at=EXCLUDED.acknowledged_at, "
                "resolved_at=EXCLUDED.resolved_at, "
                "updated_at=EXCLUDED.updated_at",
            )
            .mode("append")
            .save()
        )
    except Exception as exc:
        logger.error("JDBC write failed for batch %s: %s", batch_id, exc)

    # Write breach flags to Redis
    try:
        r = get_redis_client()
        breached_rows = batch_df.filter(
            F.col("ack_sla_breached") | F.col("res_sla_breached")
        ).select("feedback_id", "ack_sla_breached", "res_sla_breached").collect()

        pipe = r.pipeline(transaction=False)
        for row in breached_rows:
            if row["ack_sla_breached"]:
                pipe.set(f"sla:breach:ack:{row['feedback_id']}", "1", ex=86400)
            if row["res_sla_breached"]:
                pipe.set(f"sla:breach:res:{row['feedback_id']}", "1", ex=86400)
        pipe.execute()
        r.close()
    except Exception as exc:
        logger.error("Redis write failed for batch %s: %s", batch_id, exc)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    spark = create_spark_session("sla_monitor", streaming=True)
    spark.sparkContext.setLogLevel("WARN")

    raw_df = (
        spark.readStream.format("kafka")
        .options(**kafka_read_options(TOPIC_FEEDBACK_EVENTS))
        .load()
    )

    # Decode Kafka value (bytes → string) and parse JSON
    parsed_df = raw_df.select(
        F.col("timestamp").alias("kafka_ts"),
        F.from_json(F.col("value").cast("string"), EVENT_SCHEMA).alias("data"),
    ).select(
        F.col("kafka_ts"),
        F.col("data.*"),
    )

    # Add watermark on kafka timestamp for timeout-based expiry
    watermarked_df = parsed_df.withWatermark("kafka_ts", "60 seconds")

    # Apply stateful SLA tracking
    sla_df = (
        watermarked_df.groupBy("feedback_id")
        .applyInPandasWithState(
            update_sla_state,
            OUTPUT_SCHEMA,
            STATE_SCHEMA,
            "Update",
            GroupStateTimeout.EventTimeTimeout,
        )
    )

    query = (
        sla_df.writeStream.foreachBatch(write_sla_batch)
        .option(
            "checkpointLocation",
            "/tmp/spark_checkpoints/sla_monitor",
        )
        .trigger(processingTime="30 seconds")
        .start()
    )

    logger.info("SLA Monitor streaming query started: %s", query.id)
    query.awaitTermination()


if __name__ == "__main__":
    main()

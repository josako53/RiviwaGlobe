"""
Live Dashboard – PySpark Structured Streaming micro-batch job.

Reads `riviwa.feedback.events` with a 30-second trigger.
Each micro-batch is aggregated to produce per-project counters:
  - open_grievances
  - resolved_today
  - critical_open
  - overdue_count (past target_resolution_date and not resolved)

Counters are stored in Redis with a 120-second TTL so the API layer
always sees a near-real-time snapshot.

Redis key scheme
----------------
  dashboard:{project_id}:open_grievances   -> int
  dashboard:{project_id}:resolved_today    -> int
  dashboard:{project_id}:critical_open     -> int
  dashboard:{project_id}:overdue_count     -> int
  dashboard:{project_id}:last_updated      -> ISO-8601 timestamp
"""
from __future__ import annotations

import sys
import logging
from datetime import datetime, timezone, date

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType,
    StructField,
    StringType,
    TimestampType,
)

sys.path.insert(0, "/app")

from lib.spark_factory import create_spark_session
from lib.db_config import get_redis_client
from lib.kafka_config import kafka_read_options, TOPIC_FEEDBACK_EVENTS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("live_dashboard")

# ---------------------------------------------------------------------------
# Kafka event schema
# ---------------------------------------------------------------------------

EVENT_SCHEMA = StructType(
    [
        StructField("feedback_id", StringType(), True),
        StructField("project_id", StringType(), True),
        StructField("feedback_type", StringType(), True),
        StructField("priority", StringType(), True),
        StructField("category", StringType(), True),
        StructField("event_type", StringType(), True),
        StructField("status", StringType(), True),
        StructField("submitted_at", StringType(), True),
        StructField("resolved_at", StringType(), True),
        StructField("target_resolution_date", StringType(), True),
    ]
)

DASHBOARD_TTL = 120  # seconds


# ---------------------------------------------------------------------------
# foreachBatch writer
# ---------------------------------------------------------------------------

def write_dashboard_batch(batch_df: DataFrame, batch_id: int) -> None:
    """
    Aggregate each micro-batch and update Redis dashboard counters.

    We treat each batch as a delta – the streaming source delivers *events*,
    not full state.  We therefore only increment/decrement relative counters
    rather than trying to reconstruct absolute totals from events alone.
    Instead we recompute each metric strictly from the events seen in this
    batch, then INCRBY in Redis so values accumulate across batches.
    For a production-grade implementation, absolute totals would be
    reconciled hourly by the batch job `historical_analytics.py`.
    """
    if batch_df.isEmpty():
        return

    try:
        today_str = date.today().isoformat()

        # ---- 1. Compute per-project deltas from this batch ------------------

        # Open (submitted / acknowledged / in-progress events arriving → +1 open)
        open_delta = (
            batch_df.filter(
                F.col("event_type").isin(
                    "feedback.submitted", "feedback.acknowledged", "feedback.in_progress"
                )
                & ~F.col("feedback_type").isin(["resolved", "closed"])
            )
            .groupBy("project_id")
            .agg(F.count("*").alias("open_delta"))
        )

        # Close events → -1 open
        close_delta = (
            batch_df.filter(
                F.col("event_type").isin("feedback.resolved", "feedback.closed")
            )
            .groupBy("project_id")
            .agg(F.count("*").alias("close_delta"))
        )

        # Resolved today
        resolved_today = (
            batch_df.filter(
                (F.col("event_type") == "feedback.resolved")
                & (F.col("resolved_at").startswith(today_str))
            )
            .groupBy("project_id")
            .agg(F.count("*").alias("resolved_today_delta"))
        )

        # Critical open
        critical_delta = (
            batch_df.filter(
                (F.col("priority") == "critical")
                & F.col("event_type").isin(
                    "feedback.submitted", "feedback.acknowledged"
                )
            )
            .groupBy("project_id")
            .agg(F.count("*").alias("critical_delta"))
        )

        critical_resolved = (
            batch_df.filter(
                (F.col("priority") == "critical")
                & F.col("event_type").isin("feedback.resolved", "feedback.closed")
            )
            .groupBy("project_id")
            .agg(F.count("*").alias("critical_close_delta"))
        )

        # Overdue: past target_resolution_date and not yet resolved
        now_ts = F.lit(datetime.now(timezone.utc)).cast(TimestampType())
        overdue_delta = (
            batch_df.filter(
                F.col("event_type").isin("feedback.submitted", "feedback.acknowledged")
                & F.col("target_resolution_date").isNotNull()
                & (
                    F.to_timestamp("target_resolution_date").cast("long")
                    < now_ts.cast("long")
                )
                & F.col("resolved_at").isNull()
            )
            .groupBy("project_id")
            .agg(F.count("*").alias("overdue_delta"))
        )

        # ---- 2. Collect all project_ids touched in this batch ---------------

        all_projects = set(
            r["project_id"]
            for r in batch_df.select("project_id").distinct().collect()
            if r["project_id"]
        )

        # Collect deltas
        open_d = {r["project_id"]: r["open_delta"] for r in open_delta.collect()}
        close_d = {r["project_id"]: r["close_delta"] for r in close_delta.collect()}
        res_today_d = {
            r["project_id"]: r["resolved_today_delta"]
            for r in resolved_today.collect()
        }
        crit_d = {
            r["project_id"]: r["critical_delta"] for r in critical_delta.collect()
        }
        crit_close_d = {
            r["project_id"]: r["critical_close_delta"]
            for r in critical_resolved.collect()
        }
        overdue_d = {
            r["project_id"]: r["overdue_delta"] for r in overdue_delta.collect()
        }

        # ---- 3. Write to Redis ----------------------------------------------
        r = get_redis_client()
        pipe = r.pipeline(transaction=False)
        now_iso = datetime.now(timezone.utc).isoformat()

        for pid in all_projects:
            net_open = open_d.get(pid, 0) - close_d.get(pid, 0)
            net_critical = crit_d.get(pid, 0) - crit_close_d.get(pid, 0)

            if net_open != 0:
                key = f"dashboard:{pid}:open_grievances"
                pipe.incrby(key, net_open)
                pipe.expire(key, DASHBOARD_TTL)

            if res_today_d.get(pid, 0) > 0:
                key = f"dashboard:{pid}:resolved_today"
                pipe.incrby(key, res_today_d[pid])
                pipe.expire(key, DASHBOARD_TTL)

            if net_critical != 0:
                key = f"dashboard:{pid}:critical_open"
                pipe.incrby(key, net_critical)
                pipe.expire(key, DASHBOARD_TTL)

            if overdue_d.get(pid, 0) > 0:
                key = f"dashboard:{pid}:overdue_count"
                pipe.incrby(key, overdue_d[pid])
                pipe.expire(key, DASHBOARD_TTL)

            # Always update last_updated
            ts_key = f"dashboard:{pid}:last_updated"
            pipe.set(ts_key, now_iso, ex=DASHBOARD_TTL)

        pipe.execute()
        r.close()
        logger.info(
            "Dashboard updated for %d projects in batch %s", len(all_projects), batch_id
        )

    except Exception as exc:
        logger.error("live_dashboard batch %s failed: %s", batch_id, exc)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    spark = create_spark_session("live_dashboard", streaming=True)
    spark.sparkContext.setLogLevel("WARN")

    raw_df = (
        spark.readStream.format("kafka")
        .options(**kafka_read_options(TOPIC_FEEDBACK_EVENTS))
        .load()
    )

    parsed_df = raw_df.select(
        F.col("timestamp").alias("kafka_ts"),
        F.from_json(F.col("value").cast("string"), EVENT_SCHEMA).alias("data"),
    ).select(
        F.col("kafka_ts"),
        F.col("data.*"),
    )

    query = (
        parsed_df.writeStream.foreachBatch(write_dashboard_batch)
        .option("checkpointLocation", "/tmp/spark_checkpoints/live_dashboard")
        .trigger(processingTime="30 seconds")
        .start()
    )

    logger.info("Live Dashboard streaming query started: %s", query.id)
    query.awaitTermination()


if __name__ == "__main__":
    main()

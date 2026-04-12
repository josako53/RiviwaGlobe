"""
Hotspot Detector – PySpark Structured Streaming job.

Reads `riviwa.feedback.events`, keeps only `feedback.submitted` grievance
events, then applies a sliding 60-minute / 15-minute window grouped by
(project_id, issue_lga, category).  Counts are compared against a 7-day
rolling baseline loaded from analytics_db at startup (broadcast join).
When count > baseline_avg × 2.0 AND count >= 5, an alert row is written
to analytics_db.hotspot_alerts and a Redis key is set.
"""

import sys
import logging
from datetime import datetime, timezone

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType,
    StructField,
    StringType,
    IntegerType,
    DoubleType,
    TimestampType,
)

sys.path.insert(0, "/app")

from lib.spark_factory import create_spark_session
from lib.db_config import (
    ANALYTICS_JDBC_URL,
    ANALYTICS_JDBC_PROPS,
    FEEDBACK_JDBC_URL,
    FEEDBACK_JDBC_PROPS,
    get_redis_client,
)
from lib.kafka_config import kafka_read_options, TOPIC_FEEDBACK_EVENTS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hotspot_detector")

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
        StructField("issue_lga", StringType(), True),
        StructField("issue_ward", StringType(), True),
        StructField("issue_region", StringType(), True),
        StructField("submitted_at", StringType(), True),
    ]
)

HOTSPOT_THRESHOLD_MULTIPLIER = 2.0
HOTSPOT_MIN_COUNT = 5


# ---------------------------------------------------------------------------
# Load 7-day baseline from analytics_db (run once at startup, broadcast)
# ---------------------------------------------------------------------------

def load_baseline(spark: SparkSession) -> "Broadcast":  # noqa: F821
    """
    Read or compute the 7-day rolling baseline of grievance submissions
    grouped by (project_id, issue_lga, category).

    If the baseline table does not yet exist we fall back to reading raw
    feedbacks from feedback_db.
    """
    try:
        baseline_df = (
            spark.read.format("jdbc")
            .option("url", ANALYTICS_JDBC_URL)
            .option("dbtable", "(SELECT project_id, issue_lga, category, baseline_avg "
                               " FROM hotspot_baseline_7d) q")
            .option("user", ANALYTICS_JDBC_PROPS["user"])
            .option("password", ANALYTICS_JDBC_PROPS["password"])
            .option("driver", ANALYTICS_JDBC_PROPS["driver"])
            .load()
        )
        logger.info("Loaded baseline from analytics_db.hotspot_baseline_7d")
    except Exception as exc:
        logger.warning("Could not load hotspot_baseline_7d (%s) – computing from feedback_db", exc)
        # Compute 7-day baseline from raw feedbacks
        since_ts = datetime.now(timezone.utc).timestamp() - 7 * 86400
        baseline_df = (
            spark.read.format("jdbc")
            .option("url", FEEDBACK_JDBC_URL)
            .option(
                "dbtable",
                f"(SELECT project_id, issue_lga, category, "
                f" COUNT(*)::float / 7.0 AS baseline_avg "
                f" FROM feedbacks "
                f" WHERE feedback_type='grievance' "
                f"   AND submitted_at >= to_timestamp({since_ts}) "
                f" GROUP BY project_id, issue_lga, category) q",
            )
            .option("user", FEEDBACK_JDBC_PROPS["user"])
            .option("password", FEEDBACK_JDBC_PROPS["password"])
            .option("driver", FEEDBACK_JDBC_PROPS["driver"])
            .load()
        )

    # Cache and broadcast
    baseline_df.cache()
    logger.info("Baseline row count: %d", baseline_df.count())
    return spark.sparkContext.broadcast(
        {
            (r["project_id"], r["issue_lga"] or "", r["category"] or ""): r["baseline_avg"]
            for r in baseline_df.collect()
        }
    )


# ---------------------------------------------------------------------------
# foreachBatch writer
# ---------------------------------------------------------------------------

def write_hotspot_batch(batch_df: DataFrame, batch_id: int, baseline_bc) -> None:
    """Filter hotspots and write alerts to analytics_db + Redis."""
    if batch_df.isEmpty():
        return

    baseline = baseline_bc.value

    try:
        rows = batch_df.collect()
    except Exception as exc:
        logger.error("Collect failed for batch %s: %s", batch_id, exc)
        return

    alert_rows = []
    redis_cmds = []

    for row in rows:
        key = (
            row["project_id"] or "",
            row["issue_lga"] or "",
            row["category"] or "",
        )
        count = int(row["event_count"])
        baseline_avg = baseline.get(key, 0.0)

        is_hotspot = count >= HOTSPOT_MIN_COUNT and (
            baseline_avg == 0 or count > baseline_avg * HOTSPOT_THRESHOLD_MULTIPLIER
        )

        if is_hotspot:
            alert_rows.append(
                {
                    "project_id": row["project_id"],
                    "issue_lga": row["issue_lga"],
                    "category": row["category"],
                    "window_start": row["window_start"],
                    "window_end": row["window_end"],
                    "event_count": count,
                    "baseline_avg": float(baseline_avg),
                    "detected_at": datetime.now(timezone.utc),
                }
            )
            rkey = f"hotspot:{row['project_id']}:{row['issue_lga']}:{row['category']}"
            redis_cmds.append((rkey, str(count)))

    if not alert_rows:
        return

    # Write to analytics_db
    try:
        spark_session = SparkSession.getActiveSession()
        alert_schema = StructType(
            [
                StructField("project_id", StringType(), True),
                StructField("issue_lga", StringType(), True),
                StructField("category", StringType(), True),
                StructField("window_start", TimestampType(), True),
                StructField("window_end", TimestampType(), True),
                StructField("event_count", IntegerType(), True),
                StructField("baseline_avg", DoubleType(), True),
                StructField("detected_at", TimestampType(), True),
            ]
        )
        alert_df = spark_session.createDataFrame(alert_rows, schema=alert_schema)
        (
            alert_df.write.format("jdbc")
            .option("url", ANALYTICS_JDBC_URL)
            .option("dbtable", "hotspot_alerts")
            .option("user", ANALYTICS_JDBC_PROPS["user"])
            .option("password", ANALYTICS_JDBC_PROPS["password"])
            .option("driver", ANALYTICS_JDBC_PROPS["driver"])
            .mode("append")
            .save()
        )
        logger.info("Wrote %d hotspot alerts for batch %s", len(alert_rows), batch_id)
    except Exception as exc:
        logger.error("JDBC write failed for batch %s: %s", batch_id, exc)

    # Update Redis
    try:
        r = get_redis_client()
        pipe = r.pipeline(transaction=False)
        for rkey, count_val in redis_cmds:
            pipe.set(rkey, count_val, ex=3600)
        pipe.execute()
        r.close()
    except Exception as exc:
        logger.error("Redis write failed for batch %s: %s", batch_id, exc)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    spark = create_spark_session("hotspot_detector", streaming=True)
    spark.sparkContext.setLogLevel("WARN")

    # Load baseline once (broadcast)
    baseline_bc = load_baseline(spark)

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

    # Keep only submitted grievances
    grievances_df = parsed_df.filter(
        (F.col("event_type") == "feedback.submitted")
        & (F.col("feedback_type") == "grievance")
    )

    # Add watermark then sliding window aggregation
    windowed_df = (
        grievances_df.withWatermark("kafka_ts", "10 minutes")
        .groupBy(
            F.window(F.col("kafka_ts"), "60 minutes", "15 minutes").alias("w"),
            F.col("project_id"),
            F.col("issue_lga"),
            F.col("category"),
        )
        .agg(F.count("*").alias("event_count"))
        .select(
            F.col("w.start").alias("window_start"),
            F.col("w.end").alias("window_end"),
            F.col("project_id"),
            F.col("issue_lga"),
            F.col("category"),
            F.col("event_count"),
        )
    )

    # Use a closure to pass the broadcast variable into foreachBatch
    def _write(batch_df: DataFrame, batch_id: int) -> None:
        write_hotspot_batch(batch_df, batch_id, baseline_bc)

    query = (
        windowed_df.writeStream.foreachBatch(_write)
        .option("checkpointLocation", "/tmp/spark_checkpoints/hotspot_detector")
        .outputMode("update")
        .trigger(processingTime="60 seconds")
        .start()
    )

    logger.info("Hotspot Detector streaming query started: %s", query.id)
    query.awaitTermination()


if __name__ == "__main__":
    main()

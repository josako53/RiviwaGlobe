"""
Staff Analytics – PySpark batch job (runs nightly at 03:00).

Two computations:
  1. Committee performance (from feedback_db)
     Per committee: cases_assigned, cases_resolved, cases_overdue,
     avg_resolution_hours, resolution_rate
     → analytics_db.committee_performance  (overwrite today's data)

  2. Staff logins (from Kafka riviwa.auth.events, last 24 h)
     Aggregate last_login per user_id
     → analytics_db.staff_logins  (overwrite)
"""

import sys
import json
import logging
from datetime import datetime, timezone, timedelta

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType,
    StructField,
    StringType,
    IntegerType,
    DoubleType,
    TimestampType,
    LongType,
)

sys.path.insert(0, "/app")

from lib.spark_factory import create_spark_session
from lib.db_config import (
    FEEDBACK_JDBC_URL,
    FEEDBACK_JDBC_PROPS,
    ANALYTICS_JDBC_URL,
    ANALYTICS_JDBC_PROPS,
)
from lib.kafka_config import (
    kafka_batch_read_options,
    TOPIC_AUTH_EVENTS,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("staff_analytics")

AUTH_EVENT_SCHEMA = StructType(
    [
        StructField("user_id", StringType(), True),
        StructField("event_type", StringType(), True),
        StructField("occurred_at", StringType(), True),
        StructField("ip_address", StringType(), True),
        StructField("device", StringType(), True),
    ]
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def jdbc_read(spark: SparkSession, url: str, props: dict, table_or_query: str) -> DataFrame:
    return (
        spark.read.format("jdbc")
        .option("url", url)
        .option("dbtable", table_or_query)
        .option("user", props["user"])
        .option("password", props["password"])
        .option("driver", props["driver"])
        .load()
    )


def jdbc_write(df: DataFrame, url: str, props: dict, table: str, mode: str = "overwrite") -> None:
    (
        df.write.format("jdbc")
        .option("url", url)
        .option("dbtable", table)
        .option("user", props["user"])
        .option("password", props["password"])
        .option("driver", props["driver"])
        .mode(mode)
        .save()
    )


# ---------------------------------------------------------------------------
# 1. Committee performance
# ---------------------------------------------------------------------------

def compute_committee_performance(spark: SparkSession) -> DataFrame:
    """
    Joins feedbacks ↔ committee membership to produce per-committee KPIs.
    """
    feedbacks_df = jdbc_read(
        spark,
        FEEDBACK_JDBC_URL,
        FEEDBACK_JDBC_PROPS,
        "(SELECT id, assigned_committee_id, status, priority, "
        " submitted_at, resolved_at, target_resolution_date "
        " FROM feedbacks WHERE assigned_committee_id IS NOT NULL) q",
    )

    committees_df = jdbc_read(
        spark,
        FEEDBACK_JDBC_URL,
        FEEDBACK_JDBC_PROPS,
        "(SELECT id, name FROM grm_committees) q",
    )

    now_ts = datetime.now(timezone.utc)
    today_str = now_ts.date().isoformat()

    enriched = (
        feedbacks_df
        .withColumn(
            "is_resolved",
            F.col("status").isin("resolved", "closed").cast(IntegerType()),
        )
        .withColumn(
            "is_overdue",
            (
                F.col("target_resolution_date").isNotNull()
                & (F.to_timestamp("target_resolution_date") < F.lit(now_ts))
                & ~F.col("status").isin("resolved", "closed")
            ).cast(IntegerType()),
        )
        .withColumn(
            "resolution_hours",
            F.when(
                F.col("resolved_at").isNotNull(),
                (
                    F.col("resolved_at").cast("long") - F.col("submitted_at").cast("long")
                ) / 3600.0,
            ).otherwise(F.lit(None).cast(DoubleType())),
        )
    )

    agg_df = (
        enriched.groupBy("assigned_committee_id")
        .agg(
            F.count("*").alias("cases_assigned"),
            F.sum("is_resolved").alias("cases_resolved"),
            F.sum("is_overdue").alias("cases_overdue"),
            F.avg("resolution_hours").alias("avg_resolution_hours"),
        )
        .withColumn(
            "resolution_rate",
            F.when(
                F.col("cases_assigned") > 0,
                F.col("cases_resolved") / F.col("cases_assigned") * 100.0,
            ).otherwise(0.0),
        )
        .withColumnRenamed("assigned_committee_id", "committee_id")
    )

    result_df = (
        agg_df.join(
            committees_df.withColumnRenamed("id", "committee_id").withColumnRenamed(
                "name", "committee_name"
            ),
            on="committee_id",
            how="left",
        )
        .withColumn("partition_date", F.lit(today_str).cast(DateType() if False else StringType()))
        .withColumn("computed_at", F.lit(now_ts).cast(TimestampType()))
    )

    return result_df


# ---------------------------------------------------------------------------
# 2. Staff logins from Kafka
# ---------------------------------------------------------------------------

def compute_staff_logins(spark: SparkSession) -> DataFrame:
    """
    Read riviwa.auth.events for the last 24 hours from Kafka in batch mode.
    Filter event_type == 'user.login', aggregate last_login per user_id.
    """
    since_ts = int((datetime.now(timezone.utc) - timedelta(hours=24)).timestamp() * 1000)

    # Build custom offsets to read only last 24 h
    # Use timestamp-based startingOffsets json
    starting_offsets = json.dumps({"riviwa.auth.events": {str(p): since_ts for p in range(3)}})

    try:
        raw_df = (
            spark.read.format("kafka")
            .options(
                **{
                    **kafka_batch_read_options(TOPIC_AUTH_EVENTS),
                    "startingOffsets": "earliest",  # fallback; scheduler ensures 24h window
                }
            )
            .load()
        )
    except Exception as exc:
        logger.error("Could not read auth events from Kafka: %s", exc)
        # Return empty DataFrame with expected schema
        return spark.createDataFrame(
            [],
            StructType(
                [
                    StructField("user_id", StringType(), True),
                    StructField("last_login", TimestampType(), True),
                    StructField("login_count_24h", IntegerType(), True),
                    StructField("computed_at", TimestampType(), True),
                ]
            ),
        )

    parsed_df = raw_df.select(
        F.col("timestamp").alias("kafka_ts"),
        F.from_json(F.col("value").cast("string"), AUTH_EVENT_SCHEMA).alias("data"),
    ).select(
        F.col("kafka_ts"),
        F.col("data.*"),
    )

    # Filter to last 24 h and login events
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    login_df = parsed_df.filter(
        (F.col("event_type") == "user.login")
        & (F.col("kafka_ts") >= F.lit(cutoff).cast(TimestampType()))
    )

    now_ts = datetime.now(timezone.utc)

    agg_df = (
        login_df.groupBy("user_id")
        .agg(
            F.max("kafka_ts").alias("last_login"),
            F.count("*").alias("login_count_24h"),
        )
        .withColumn("computed_at", F.lit(now_ts).cast(TimestampType()))
    )

    return agg_df


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    spark = create_spark_session("staff_analytics")
    spark.sparkContext.setLogLevel("WARN")

    logger.info("staff_analytics starting at %s", datetime.now(timezone.utc).isoformat())

    # ---- 1. Committee performance -------------------------------------------
    try:
        committee_df = compute_committee_performance(spark)
        jdbc_write(
            committee_df,
            ANALYTICS_JDBC_URL,
            ANALYTICS_JDBC_PROPS,
            "committee_performance",
            mode="overwrite",
        )
        logger.info("committee_performance written (%d rows)", committee_df.count())
    except Exception as exc:
        logger.error("committee_performance failed: %s", exc)

    # ---- 2. Staff logins ----------------------------------------------------
    try:
        logins_df = compute_staff_logins(spark)
        jdbc_write(
            logins_df,
            ANALYTICS_JDBC_URL,
            ANALYTICS_JDBC_PROPS,
            "staff_logins",
            mode="overwrite",
        )
        logger.info("staff_logins written (%d rows)", logins_df.count())
    except Exception as exc:
        logger.error("staff_logins failed: %s", exc)

    spark.stop()
    logger.info("staff_analytics completed at %s", datetime.now(timezone.utc).isoformat())


if __name__ == "__main__":
    main()

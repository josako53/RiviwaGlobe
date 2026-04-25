"""
Historical Analytics – PySpark batch job (runs hourly at :00).

Reads feedback_db tables and writes pre-aggregated analytics to
analytics_db.  Four computations are performed:

  1. Status distribution per project / feedback_type / status
     → analytics_db.analytics_status_counts  (overwrite)

  2. SLA compliance per project / priority
     → analytics_db.analytics_sla_compliance  (overwrite)

  3. Daily trend: submitted vs resolved counts
     → analytics_db.analytics_daily_trend  (overwrite)

  4. Update feedback_sla_status with days_unresolved for open feedbacks
     → analytics_db.feedback_sla_status  (upsert via temp view + JDBC overwrite)
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
    BooleanType,
    TimestampType,
    DateType,
)

sys.path.insert(0, "/app")

from lib.spark_factory import create_spark_session
from lib.db_config import (
    FEEDBACK_JDBC_URL,
    FEEDBACK_JDBC_PROPS,
    ANALYTICS_JDBC_URL,
    ANALYTICS_JDBC_PROPS,
)
from lib.kafka_config import ACK_SLA_HOURS, RES_SLA_HOURS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("historical_analytics")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def jdbc_read(spark: SparkSession, url: str, props: dict, table_or_query: str) -> DataFrame:
    """Read a JDBC table or sub-query DataFrame."""
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
    """Write a DataFrame to a JDBC table."""
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
# 1. Status distribution
# ---------------------------------------------------------------------------

def compute_status_distribution(feedbacks_df: DataFrame) -> DataFrame:
    """
    Returns: project_id, feedback_type, status, count, computed_at
    """
    now = datetime.now(timezone.utc)
    return (
        feedbacks_df.groupBy("project_id", "feedback_type", "status")
        .agg(F.count("*").alias("count"))
        .withColumn("computed_at", F.lit(now).cast(TimestampType()))
    )


# ---------------------------------------------------------------------------
# 2. SLA compliance
# ---------------------------------------------------------------------------

def compute_sla_compliance(feedbacks_df: DataFrame) -> DataFrame:
    """
    Per project_id / priority:
      - avg_ack_hours, median_ack_hours
      - avg_res_hours, median_res_hours
      - total_count, ack_sla_met_count, res_sla_met_count
      - ack_compliance_pct, res_compliance_pct
    """
    # Build a mapping from priority → SLA target hours (as a Spark map)
    ack_sla_map = F.create_map(
        *[v for pair in [(F.lit(k), F.lit(v)) for k, v in ACK_SLA_HOURS.items()] for v in pair]
    )
    res_sla_map = F.create_map(
        *[v for pair in [(F.lit(k), F.lit(v)) for k, v in RES_SLA_HOURS.items()] for v in pair]
    )

    enriched = feedbacks_df.withColumn(
        "ack_hours",
        F.when(
            F.col("acknowledged_at").isNotNull(),
            (
                F.col("acknowledged_at").cast("long") - F.col("submitted_at").cast("long")
            ) / 3600.0,
        ).otherwise(F.lit(None).cast(DoubleType())),
    ).withColumn(
        "res_hours",
        F.when(
            F.col("resolved_at").isNotNull(),
            (
                F.col("resolved_at").cast("long") - F.col("submitted_at").cast("long")
            ) / 3600.0,
        ).otherwise(F.lit(None).cast(DoubleType())),
    ).withColumn(
        "priority_lower", F.lower(F.col("priority"))
    ).withColumn(
        "ack_sla_target", ack_sla_map[F.col("priority_lower")]
    ).withColumn(
        "res_sla_target", res_sla_map[F.col("priority_lower")]
    ).withColumn(
        "ack_sla_met",
        F.when(
            F.col("ack_hours").isNotNull() & F.col("ack_sla_target").isNotNull(),
            F.col("ack_hours") <= F.col("ack_sla_target"),
        ).otherwise(F.lit(None).cast(BooleanType())),
    ).withColumn(
        "res_sla_met",
        F.when(
            F.col("res_hours").isNotNull() & F.col("res_sla_target").isNotNull(),
            F.col("res_hours") <= F.col("res_sla_target"),
        ).otherwise(F.lit(None).cast(BooleanType())),
    )

    now = datetime.now(timezone.utc)

    compliance_df = (
        enriched.groupBy("project_id", "priority_lower")
        .agg(
            F.count("*").alias("total_count"),
            F.avg("ack_hours").alias("avg_ack_hours"),
            F.percentile_approx("ack_hours", 0.5).alias("median_ack_hours"),
            F.avg("res_hours").alias("avg_res_hours"),
            F.percentile_approx("res_hours", 0.5).alias("median_res_hours"),
            F.sum(F.col("ack_sla_met").cast(IntegerType())).alias("ack_sla_met_count"),
            F.sum(F.col("res_sla_met").cast(IntegerType())).alias("res_sla_met_count"),
        )
        .withColumnRenamed("priority_lower", "priority")
        .withColumn(
            "ack_compliance_pct",
            F.when(
                F.col("total_count") > 0,
                F.col("ack_sla_met_count") / F.col("total_count") * 100.0,
            ).otherwise(0.0),
        )
        .withColumn(
            "res_compliance_pct",
            F.when(
                F.col("total_count") > 0,
                F.col("res_sla_met_count") / F.col("total_count") * 100.0,
            ).otherwise(0.0),
        )
        .withColumn("computed_at", F.lit(now).cast(TimestampType()))
    )

    return compliance_df


# ---------------------------------------------------------------------------
# 3. Daily trend
# ---------------------------------------------------------------------------

def compute_daily_trend(feedbacks_df: DataFrame) -> DataFrame:
    """
    Returns per (project_id, feedback_type, submitted_date):
      submitted_count, resolved_count
    """
    submitted = (
        feedbacks_df.withColumn("submitted_date", F.to_date("submitted_at"))
        .groupBy("project_id", "feedback_type", "submitted_date")
        .agg(F.count("*").alias("submitted_count"))
    )

    resolved2 = (
        feedbacks_df.filter(F.col("resolved_at").isNotNull())
        .withColumn("submitted_date", F.to_date("resolved_at"))
        .groupBy("project_id", "feedback_type", "submitted_date")
        .agg(F.count("*").alias("resolved_count"))
    )

    trend_df = submitted.join(
        resolved2,
        on=["project_id", "feedback_type", "submitted_date"],
        how="left",
    ).select(
        submitted["project_id"],
        submitted["feedback_type"],
        submitted["submitted_date"],
        submitted["submitted_count"],
        F.coalesce(resolved2["resolved_count"], F.lit(0)).alias("resolved_count"),
    ).withColumn("computed_at", F.lit(datetime.now(timezone.utc)).cast(TimestampType()))

    return trend_df


# ---------------------------------------------------------------------------
# 4. Update days_unresolved in feedback_sla_status
# ---------------------------------------------------------------------------

def update_days_unresolved(
    spark: SparkSession,
    feedbacks_df: DataFrame,
) -> None:
    """
    For all open feedbacks compute days_unresolved = (now - submitted_at) / 86400
    then upsert into analytics_db.feedback_sla_status.
    """
    now_epoch = datetime.now(timezone.utc).timestamp()
    now_ts = datetime.now(timezone.utc)

    open_df = (
        feedbacks_df.filter(
            ~F.col("status").isin("resolved", "closed")
        )
        .withColumn(
            "days_unresolved",
            (F.lit(now_epoch) - F.col("submitted_at").cast("long")) / 86400.0,
        )
        .select(
            F.col("id").alias("feedback_id"),
            F.col("project_id"),
            F.col("priority"),
            F.col("submitted_at"),
            F.col("days_unresolved"),
            F.lit(now_ts).cast(TimestampType()).alias("updated_at"),
        )
    )

    if open_df.isEmpty():
        logger.info("No open feedbacks to update.")
        return

    # Read existing sla_status rows and merge
    try:
        existing_df = jdbc_read(
            spark,
            ANALYTICS_JDBC_URL,
            ANALYTICS_JDBC_PROPS,
            "(SELECT feedback_id, ack_deadline, res_deadline, acknowledged_at, resolved_at, "
            " ack_sla_met, ack_sla_breached, res_sla_met, res_sla_breached "
            " FROM feedback_sla_status) q",
        )
        merged_df = open_df.join(existing_df, on="feedback_id", how="left")
    except Exception as exc:
        logger.warning("Could not read existing feedback_sla_status: %s", exc)
        merged_df = open_df

    jdbc_write(merged_df, ANALYTICS_JDBC_URL, ANALYTICS_JDBC_PROPS, "feedback_sla_status", mode="overwrite")
    logger.info("Updated days_unresolved for open feedbacks.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    spark = create_spark_session("historical_analytics")
    spark.sparkContext.setLogLevel("WARN")

    logger.info("historical_analytics starting at %s", datetime.now(timezone.utc).isoformat())

    # ---- Read source tables --------------------------------------------------
    feedbacks_df = jdbc_read(
        spark,
        FEEDBACK_JDBC_URL,
        FEEDBACK_JDBC_PROPS,
        "(SELECT id, feedback_type, status, priority, category, project_id, "
        " submitted_at, acknowledged_at, resolved_at, target_resolution_date, "
        " assigned_to_user_id, assigned_committee_id, "
        " issue_lga, issue_ward, issue_region, updated_at "
        " FROM feedbacks) q",
    )
    feedbacks_df.cache()
    logger.info("Read %d feedbacks", feedbacks_df.count())

    # ---- 1. Status distribution ---------------------------------------------
    try:
        status_df = compute_status_distribution(feedbacks_df)
        jdbc_write(
            status_df,
            ANALYTICS_JDBC_URL,
            ANALYTICS_JDBC_PROPS,
            "analytics_status_counts",
            mode="overwrite",
        )
        logger.info("analytics_status_counts written")
    except Exception as exc:
        logger.error("Status distribution failed: %s", exc)

    # ---- 2. SLA compliance --------------------------------------------------
    try:
        compliance_df = compute_sla_compliance(feedbacks_df)
        jdbc_write(
            compliance_df,
            ANALYTICS_JDBC_URL,
            ANALYTICS_JDBC_PROPS,
            "analytics_sla_compliance",
            mode="overwrite",
        )
        logger.info("analytics_sla_compliance written")
    except Exception as exc:
        logger.error("SLA compliance failed: %s", exc)

    # ---- 3. Daily trend -----------------------------------------------------
    try:
        trend_df = compute_daily_trend(feedbacks_df)
        jdbc_write(
            trend_df,
            ANALYTICS_JDBC_URL,
            ANALYTICS_JDBC_PROPS,
            "analytics_daily_trend",
            mode="overwrite",
        )
        logger.info("analytics_daily_trend written")
    except Exception as exc:
        logger.error("Daily trend failed: %s", exc)

    # ---- 4. Update days_unresolved ------------------------------------------
    try:
        update_days_unresolved(spark, feedbacks_df)
    except Exception as exc:
        logger.error("days_unresolved update failed: %s", exc)

    feedbacks_df.unpersist()
    spark.stop()
    logger.info("historical_analytics completed at %s", datetime.now(timezone.utc).isoformat())


if __name__ == "__main__":
    main()

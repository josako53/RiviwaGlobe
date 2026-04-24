"""
ML Escalation Scorer – PySpark MLlib batch job (runs nightly at 04:00).

Pipeline:
  1. Read feedbacks + feedback_escalations + feedback_actions from feedback_db
  2. Engineer features
  3. Train GBTClassifier on labelled data (will_escalate = 1 if any escalation)
  4. Evaluate AUC on 20% test split
  5. Score all currently open feedbacks
  6. Write predictions to analytics_db.feedback_ml_scores

Output schema: feedback_id, escalation_probability, predicted_resolution_hours (null),
               recommended_priority, scored_at
"""

from __future__ import annotations

import sys
import logging
from datetime import datetime, timezone

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType,
    StructField,
    StringType,
    DoubleType,
    IntegerType,
    TimestampType,
)
from pyspark.ml import Pipeline
from pyspark.ml.feature import StringIndexer, VectorAssembler, StandardScaler
from pyspark.ml.classification import GBTClassifier
from pyspark.ml.evaluation import BinaryClassificationEvaluator

sys.path.insert(0, "/app")

from lib.spark_factory import create_spark_session
from lib.db_config import (
    FEEDBACK_JDBC_URL,
    FEEDBACK_JDBC_PROPS,
    ANALYTICS_JDBC_URL,
    ANALYTICS_JDBC_PROPS,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ml_escalation")

# ---------------------------------------------------------------------------
# Priority thresholds for recommended_priority
# ---------------------------------------------------------------------------

# If escalation_probability >= threshold, recommend upgrading priority
UPGRADE_CRITICAL_THRESHOLD = 0.85
UPGRADE_HIGH_THRESHOLD = 0.65


def get_recommended_priority(prob: float, current_priority: str) -> str:
    """Pure-Python helper – used via a UDF."""
    if prob >= UPGRADE_CRITICAL_THRESHOLD:
        return "critical"
    if prob >= UPGRADE_HIGH_THRESHOLD:
        return "high" if current_priority not in ("critical",) else current_priority
    return current_priority


recommended_priority_udf = F.udf(get_recommended_priority, StringType())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def jdbc_read(spark: SparkSession, url: str, props: dict, query: str) -> DataFrame:
    return (
        spark.read.format("jdbc")
        .option("url", url)
        .option("dbtable", query)
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
# Feature engineering
# ---------------------------------------------------------------------------

def build_feature_df(
    feedbacks_df: DataFrame,
    actions_df: DataFrame,
    escalations_df: DataFrame,
) -> DataFrame:
    """
    Returns a DataFrame with all feature columns and label 'will_escalate'.
    """
    now_epoch = datetime.now(timezone.utc).timestamp()

    # Count escalations per feedback
    escalation_counts = (
        escalations_df.groupBy("feedback_id")
        .agg(F.count("*").alias("escalation_count"))
    )

    # Count actions per feedback
    action_counts = (
        actions_df.groupBy("feedback_id")
        .agg(F.count("*").alias("action_count"))
    )

    # Join
    joined = (
        feedbacks_df
        .join(escalation_counts, feedbacks_df["id"] == escalation_counts["feedback_id"], "left")
        .join(action_counts, feedbacks_df["id"] == action_counts["feedback_id"], "left")
        .withColumn("escalation_count", F.coalesce(F.col("escalation_count"), F.lit(0)))
        .withColumn("action_count", F.coalesce(F.col("action_count"), F.lit(0)))
        .withColumn("will_escalate", (F.col("escalation_count") > 0).cast(IntegerType()))
        .withColumn(
            "is_anonymous",
            F.col("is_anonymous").cast(IntegerType()),
        )
        .withColumn(
            "has_voice_note",
            F.when(F.col("voice_note_url").isNotNull(), 1).otherwise(0),
        )
        .withColumn(
            "hours_since_submitted",
            (F.lit(now_epoch) - F.col("submitted_at").cast("long")) / 3600.0,
        )
        # Normalise priority and channel to lower-case strings for indexing
        .withColumn("priority_norm", F.lower(F.coalesce(F.col("priority"), F.lit("medium"))))
        .withColumn("category_norm", F.lower(F.coalesce(F.col("category"), F.lit("unknown"))))
        .withColumn("channel_norm", F.lower(F.coalesce(F.col("channel"), F.lit("unknown"))))
        .withColumn("region_norm", F.lower(F.coalesce(F.col("issue_region"), F.lit("unknown"))))
    )

    feature_df = joined.select(
        F.col("id").alias("feedback_id"),
        F.col("status"),
        F.col("priority"),
        F.col("priority_norm"),
        F.col("category_norm"),
        F.col("channel_norm"),
        F.col("region_norm"),
        F.col("is_anonymous"),
        F.col("has_voice_note"),
        F.col("action_count"),
        F.col("escalation_count"),
        F.col("hours_since_submitted"),
        F.col("will_escalate").alias("label"),
    )

    return feature_df


# ---------------------------------------------------------------------------
# ML Pipeline
# ---------------------------------------------------------------------------

def build_pipeline(categorical_cols: list[str], numeric_cols: list[str]) -> Pipeline:
    stages = []

    # StringIndexers for categorical
    indexed_cols = []
    for col in categorical_cols:
        out_col = f"{col}_idx"
        indexer = StringIndexer(
            inputCol=col,
            outputCol=out_col,
            handleInvalid="keep",
        )
        stages.append(indexer)
        indexed_cols.append(out_col)

    # VectorAssembler
    assembler = VectorAssembler(
        inputCols=indexed_cols + numeric_cols,
        outputCol="raw_features",
        handleInvalid="keep",
    )
    stages.append(assembler)

    # StandardScaler
    scaler = StandardScaler(
        inputCol="raw_features",
        outputCol="features",
        withStd=True,
        withMean=False,
    )
    stages.append(scaler)

    # GBTClassifier
    gbt = GBTClassifier(
        labelCol="label",
        featuresCol="features",
        maxIter=50,
        maxDepth=5,
        stepSize=0.1,
        seed=42,
    )
    stages.append(gbt)

    return Pipeline(stages=stages)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    spark = create_spark_session("ml_escalation")
    spark.sparkContext.setLogLevel("WARN")

    logger.info("ml_escalation starting at %s", datetime.now(timezone.utc).isoformat())

    # ---- Read source tables --------------------------------------------------
    feedbacks_df = jdbc_read(
        spark,
        FEEDBACK_JDBC_URL,
        FEEDBACK_JDBC_PROPS,
        "(SELECT id, feedback_type, status, priority, category, channel, "
        " project_id, issue_region, is_anonymous, voice_note_url, "
        " submitted_at, resolved_at "
        " FROM feedbacks) q",
    )

    escalations_df = jdbc_read(
        spark,
        FEEDBACK_JDBC_URL,
        FEEDBACK_JDBC_PROPS,
        "(SELECT id, feedback_id, escalated_at FROM feedback_escalations) q",
    )

    actions_df = jdbc_read(
        spark,
        FEEDBACK_JDBC_URL,
        FEEDBACK_JDBC_PROPS,
        "(SELECT id, feedback_id FROM feedback_actions) q",
    )

    feedbacks_df.cache()
    total = feedbacks_df.count()
    logger.info("Read %d feedbacks", total)

    if total < 100:
        logger.warning(
            "Insufficient data (%d rows) to train a meaningful model. "
            "Writing placeholder scores and exiting.",
            total,
        )
        # Write empty placeholder
        empty_df = spark.createDataFrame(
            [],
            StructType(
                [
                    StructField("feedback_id", StringType(), False),
                    StructField("escalation_probability", DoubleType(), True),
                    StructField("predicted_resolution_hours", DoubleType(), True),
                    StructField("recommended_priority", StringType(), True),
                    StructField("scored_at", TimestampType(), True),
                ]
            ),
        )
        jdbc_write(empty_df, ANALYTICS_JDBC_URL, ANALYTICS_JDBC_PROPS, "feedback_ml_scores", "overwrite")
        spark.stop()
        return

    # ---- Feature engineering ------------------------------------------------
    feature_df = build_feature_df(feedbacks_df, actions_df, escalations_df)
    feature_df.cache()

    categorical_cols = ["category_norm", "channel_norm", "priority_norm", "region_norm"]
    numeric_cols = [
        "is_anonymous",
        "has_voice_note",
        "action_count",
        "escalation_count",
        "hours_since_submitted",
    ]

    # ---- Train / test split (labelled data = historical feedbacks that are resolved/closed) ------
    labelled_df = feature_df.filter(F.col("status").isin("resolved", "closed"))
    train_df, test_df = labelled_df.randomSplit([0.8, 0.2], seed=42)

    train_count = train_df.count()
    pos_count = train_df.filter(F.col("label") == 1).count()
    logger.info(
        "Training on %d rows (%d positive / %d negative)",
        train_count,
        pos_count,
        train_count - pos_count,
    )

    if train_count < 50:
        logger.warning("Training set too small (%d). Skipping ML scoring.", train_count)
        spark.stop()
        return

    # ---- Build and train pipeline -------------------------------------------
    pipeline = build_pipeline(categorical_cols, numeric_cols)

    try:
        model = pipeline.fit(train_df)
    except Exception as exc:
        logger.error("Pipeline training failed: %s", exc)
        spark.stop()
        return

    # ---- Evaluate on test set -----------------------------------------------
    try:
        test_predictions = model.transform(test_df)
        evaluator = BinaryClassificationEvaluator(
            labelCol="label",
            rawPredictionCol="rawPrediction",
            metricName="areaUnderROC",
        )
        auc = evaluator.evaluate(test_predictions)
        logger.info("Test AUC: %.4f", auc)
    except Exception as exc:
        logger.error("Evaluation failed: %s", exc)

    # ---- Score open feedbacks -----------------------------------------------
    open_df = feature_df.filter(~F.col("status").isin("resolved", "closed"))
    open_count = open_df.count()
    logger.info("Scoring %d open feedbacks", open_count)

    if open_count == 0:
        logger.info("No open feedbacks to score.")
        spark.stop()
        return

    try:
        scored_df = model.transform(open_df)

        # Extract probability of class 1 (will_escalate) from probability vector
        extract_prob = F.udf(lambda v: float(v[1]) if v is not None else 0.0, DoubleType())

        now_ts = datetime.now(timezone.utc)

        output_df = (
            scored_df
            .withColumn("escalation_probability", extract_prob(F.col("probability")))
            .withColumn(
                "recommended_priority",
                recommended_priority_udf(
                    F.col("escalation_probability"),
                    F.col("priority"),
                ),
            )
            .select(
                F.col("feedback_id"),
                F.col("escalation_probability"),
                F.lit(None).cast(DoubleType()).alias("predicted_resolution_hours"),
                F.col("recommended_priority"),
                F.lit(now_ts).cast(TimestampType()).alias("scored_at"),
            )
        )

        jdbc_write(
            output_df,
            ANALYTICS_JDBC_URL,
            ANALYTICS_JDBC_PROPS,
            "feedback_ml_scores",
            mode="overwrite",
        )
        logger.info("feedback_ml_scores written (%d rows)", output_df.count())
    except Exception as exc:
        logger.error("Scoring or write failed: %s", exc)

    feedbacks_df.unpersist()
    feature_df.unpersist()
    spark.stop()
    logger.info("ml_escalation completed at %s", datetime.now(timezone.utc).isoformat())


if __name__ == "__main__":
    main()

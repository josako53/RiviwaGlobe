from pyspark.sql import SparkSession


def create_spark_session(app_name: str, streaming: bool = False) -> SparkSession:
    builder = (
        SparkSession.builder.appName(app_name)
        .master("spark://spark_master:7077")
        .config(
            "spark.jars.packages",
            "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,"
            "org.postgresql:postgresql:42.6.0",
        )
        .config(
            "spark.sql.streaming.checkpointLocation",
            f"/tmp/spark_checkpoints/{app_name}",
        )
        .config("spark.driver.memory", "1g")
        .config("spark.executor.memory", "1g")
    )
    if streaming:
        builder = builder.config("spark.sql.shuffle.partitions", "4")
    return builder.getOrCreate()

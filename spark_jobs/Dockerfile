FROM apache/spark:3.5.3

USER root

# Install Python dependencies for scheduler and DB/Redis clients
RUN pip install --no-cache-dir \
    psycopg2-binary==2.9.9 \
    redis==5.2.1 \
    apscheduler==3.10.4

# netcat for healthchecks in entrypoint.sh
RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends netcat-openbsd && \
    rm -rf /var/lib/apt/lists/*

# Copy application code
COPY . /app

WORKDIR /app

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

# Create checkpoint directory
RUN mkdir -p /tmp/spark_checkpoints && chmod 777 /tmp/spark_checkpoints

# Pre-create ivy2 directories so spark-submit can write its dependency cache.
# Without these, every spark-submit with --packages crashes with
# FileNotFoundException when Ivy tries to write the resolved module descriptor.
RUN mkdir -p /home/spark/.ivy2/cache /home/spark/.ivy2/jars && \
    chown -R 185:185 /home/spark

# Pre-download Spark packages into the image so runtime launches are instant
# and don't need internet access. Uses --master local[1] (no cluster needed).
USER 185
RUN echo "from pyspark.sql import SparkSession; SparkSession.builder.getOrCreate().stop()" > /tmp/_pkg_seed.py && \
    /opt/spark/bin/spark-submit \
        --master local[1] \
        --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,org.postgresql:postgresql:42.6.0 \
        /tmp/_pkg_seed.py 2>&1 | tail -5 && \
    rm /tmp/_pkg_seed.py

USER root

# spark-submit is at /opt/spark/bin — add to PATH
ENV PATH="/opt/spark/bin:$PATH"

# Run as the default apache/spark non-root user (UID 185)
USER 185

ENTRYPOINT ["/app/entrypoint.sh"]

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

# spark-submit is at /opt/spark/bin — add to PATH
ENV PATH="/opt/spark/bin:$PATH"

# Run as the default apache/spark non-root user (UID 185)
USER 185

ENTRYPOINT ["/app/entrypoint.sh"]

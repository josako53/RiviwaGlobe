#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------------------------------
# Riviwa Spark Jobs – entrypoint
#
# Starts all three streaming jobs in the background then hands off to the
# APScheduler process which:
#   - runs batch jobs on their cron schedule
#   - monitors and restarts streaming jobs if they die
# ---------------------------------------------------------------------------

echo "[entrypoint] Starting Riviwa Spark Jobs service at $(date -u)"

SPARK_MASTER="${SPARK_MASTER:-spark://spark_master:7077}"
PACKAGES="org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,org.postgresql:postgresql:42.6.0"

# ---------------------------------------------------------------------------
# Wait for Spark master to be reachable (up to 60 s)
# ---------------------------------------------------------------------------
SPARK_MASTER_HOST=$(echo "$SPARK_MASTER" | sed 's|spark://||' | cut -d: -f1)
SPARK_MASTER_PORT=$(echo "$SPARK_MASTER" | sed 's|spark://||' | cut -d: -f2)

echo "[entrypoint] Waiting for Spark master at $SPARK_MASTER_HOST:$SPARK_MASTER_PORT …"
attempts=0
until nc -z "$SPARK_MASTER_HOST" "$SPARK_MASTER_PORT" 2>/dev/null; do
  attempts=$((attempts + 1))
  if [ "$attempts" -ge 30 ]; then
    echo "[entrypoint] ERROR: Spark master not reachable after 60 s. Aborting." >&2
    exit 1
  fi
  sleep 2
done
echo "[entrypoint] Spark master is up."

# ---------------------------------------------------------------------------
# Wait for analytics_db PostgreSQL to be reachable (up to 60 s)
# ---------------------------------------------------------------------------
ANALYTICS_DB_HOST="${ANALYTICS_DB_HOST:-analytics_db}"
ANALYTICS_DB_PORT="${ANALYTICS_DB_PORT:-5432}"

echo "[entrypoint] Waiting for analytics_db at $ANALYTICS_DB_HOST:$ANALYTICS_DB_PORT …"
attempts=0
until nc -z "$ANALYTICS_DB_HOST" "$ANALYTICS_DB_PORT" 2>/dev/null; do
  attempts=$((attempts + 1))
  if [ "$attempts" -ge 30 ]; then
    echo "[entrypoint] WARNING: analytics_db not reachable after 60 s – continuing anyway." >&2
    break
  fi
  sleep 2
done

# ---------------------------------------------------------------------------
# Start streaming jobs in the background
# (The scheduler will restart them if they crash)
# ---------------------------------------------------------------------------

echo "[entrypoint] Launching SLA Monitor …"
spark-submit \
  --master "$SPARK_MASTER" \
  --packages "$PACKAGES" \
  /app/jobs/streaming/sla_monitor.py \
  >> /tmp/sla_monitor.log 2>&1 &
SLA_PID=$!
echo "[entrypoint] SLA Monitor PID=$SLA_PID"

echo "[entrypoint] Launching Hotspot Detector …"
spark-submit \
  --master "$SPARK_MASTER" \
  --packages "$PACKAGES" \
  /app/jobs/streaming/hotspot_detector.py \
  >> /tmp/hotspot_detector.log 2>&1 &
HOTSPOT_PID=$!
echo "[entrypoint] Hotspot Detector PID=$HOTSPOT_PID"

echo "[entrypoint] Launching Live Dashboard …"
spark-submit \
  --master "$SPARK_MASTER" \
  --packages "$PACKAGES" \
  /app/jobs/streaming/live_dashboard.py \
  >> /tmp/live_dashboard.log 2>&1 &
DASHBOARD_PID=$!
echo "[entrypoint] Live Dashboard PID=$DASHBOARD_PID"

# Give streaming jobs a few seconds to initialise before the scheduler
# starts submitting batch jobs that compete for cluster resources
sleep 10

# ---------------------------------------------------------------------------
# Hand off to APScheduler (batch jobs + watchdog)
# exec replaces this shell so SIGTERM/SIGINT are forwarded directly
# ---------------------------------------------------------------------------
echo "[entrypoint] Starting APScheduler …"
exec python3 /app/scheduler.py

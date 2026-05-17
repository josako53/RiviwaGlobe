#!/bin/bash
set -e
echo "── subscription_service starting ──"
echo "[1/3] Waiting for database..."
until pg_isready -h "${SUBSCRIPTION_DB_HOST:-subscription_db}" -p "5432" -U "${SUBSCRIPTION_DB_USER:-subscription_admin}" -q; do
  sleep 1
done
echo "  Database is ready."
echo "[2/3] Running migrations..."
alembic upgrade head 2>/dev/null || echo "  Alembic skipped — using SQLModel create_all."
echo "[3/3] Starting application..."
exec "$@"

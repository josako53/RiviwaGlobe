#!/usr/bin/env bash
set -e

echo "[integration_service] Waiting for PostgreSQL..."
until pg_isready -h "${INTEGRATION_DB_HOST:-integration_db}" -p "${DB_PORT:-5432}" -U "${INTEGRATION_DB_USER:-integration_admin}" -q; do
    sleep 1
done
echo "[integration_service] PostgreSQL ready."

echo "[integration_service] Running Alembic migrations..."
alembic upgrade head
echo "[integration_service] Migrations done."

if [ "${ENVIRONMENT:-production}" = "development" ]; then
    echo "[integration_service] Starting in development mode (hot-reload)..."
    exec uvicorn main:app --host 0.0.0.0 --port 8100 --reload
else
    echo "[integration_service] Starting in production mode..."
    exec uvicorn main:app --host 0.0.0.0 --port 8100 --workers 2
fi

#!/usr/bin/env bash
set -e
echo '── qr_service starting ──'
echo '[1/3] Waiting for database...'
until pg_isready -h "${QR_DB_HOST:-qr_db}" -p "${DB_PORT:-5432}" -U "${QR_DB_USER:-qr_admin}" -q; do
  sleep 1
done
echo '  Database is ready.'
echo '[2/3] Initialising tables (create_all)...'
# No alembic — SQLModel create_all handles schema
echo '[3/3] Starting application...'
if [ "${ENVIRONMENT:-production}" = "development" ]; then
  exec uvicorn main:app --host 0.0.0.0 --port 8120 --reload
else
  exec uvicorn main:app --host 0.0.0.0 --port 8120 --workers 2
fi

#!/usr/bin/env bash
set -e
echo '── verification_service starting ──'
echo '[1/3] Waiting for database...'
until pg_isready -h "${VERIFICATION_DB_HOST:-verification_db}" -p "${DB_PORT:-5432}" -U "${VERIFICATION_DB_USER:-verification_admin}" -q; do
  sleep 1
done
echo '  Database is ready.'
echo '[2/3] Running migrations...'
alembic upgrade head 2>/dev/null || echo '  Alembic skipped — using create_all fallback.'
echo '[3/3] Starting application...'
if [ "${ENVIRONMENT:-production}" = "development" ]; then
  exec uvicorn main:app --host 0.0.0.0 --port 8125 --reload
else
  exec uvicorn main:app --host 0.0.0.0 --port 8125 --workers 2
fi

#!/usr/bin/env bash
set -e

echo "── waiting_service starting up ──────────────────"

MAX_RETRIES=30
RETRIES=0
until pg_isready -h "${WAITING_DB_HOST:-waiting_db}" -p "${DB_PORT:-5432}" \
      -U "${WAITING_DB_USER:-waiting_admin}" -q; do
  RETRIES=$((RETRIES + 1))
  if [ "$RETRIES" -ge "$MAX_RETRIES" ]; then
    echo "ERROR: Database not ready after ${MAX_RETRIES}s. Aborting."
    exit 1
  fi
  echo "  Waiting for DB... (${RETRIES}/${MAX_RETRIES})"
  sleep 1
done
echo "  Database ready."

if [ -d "alembic/versions" ] && [ "$(ls -A alembic/versions 2>/dev/null)" ]; then
  alembic upgrade head
  echo "  Migrations complete."
else
  echo "  No migrations found — init_db() will create tables on startup."
fi

exec "$@"

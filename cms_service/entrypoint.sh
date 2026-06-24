#!/usr/bin/env bash
set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Riviwa CMS Service"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

MAX_RETRIES=30
RETRIES=0
until pg_isready -h "${CMS_DB_HOST:-cms_db}" -p "${DB_PORT:-5432}" -U "${CMS_DB_USER:-cms_admin}" -q; do
  RETRIES=$((RETRIES+1))
  [ $RETRIES -ge $MAX_RETRIES ] && echo "ERROR: DB not ready after ${MAX_RETRIES}s. Exiting." && exit 1
  echo "Waiting for DB... ($RETRIES/$MAX_RETRIES)"
  sleep 1
done
echo "DB ready."

if [ -d "alembic/versions" ] && [ "$(ls -A alembic/versions 2>/dev/null)" ]; then
  alembic upgrade head && echo "Migrations complete."
else
  echo "No migrations found — skipping."
fi

echo "Starting application: $@"
echo "──────────────────────────────────────────────"
exec "$@"

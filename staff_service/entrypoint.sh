#!/usr/bin/env bash
set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Riviwa Staff Service"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── 1. Wait for PostgreSQL ──────────────────────────────────────────────────────
MAX_RETRIES=30
RETRIES=0
until pg_isready -h "${STAFF_DB_HOST:-staff_db}" -p "${DB_PORT:-5432}" -U "${STAFF_DB_USER:-staff_admin}" -q; do
  RETRIES=$((RETRIES+1))
  [ $RETRIES -ge $MAX_RETRIES ] && echo "ERROR: DB not ready after ${MAX_RETRIES}s. Exiting." && exit 1
  echo "Waiting for DB... ($RETRIES/$MAX_RETRIES)"
  sleep 1
done
echo "DB ready."

# ── 2. Run Alembic Migrations ───────────────────────────────────────────────────
if [ -d "alembic/versions" ] && [ "$(ls -A alembic/versions 2>/dev/null)" ]; then
  alembic upgrade head && echo "Migrations complete."
else
  echo "No migrations found — skipping."
fi

# ── 3. Start Application ────────────────────────────────────────────────────────
echo "Starting application: $@"
echo "──────────────────────────────────────────────"
exec "$@"

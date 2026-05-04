#!/bin/bash
set -e

DB_HOST="${PRODUCT_DB_HOST:-product_db}"
DB_PORT="${DB_PORT:-5432}"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Riviwa Product Service"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── 1. Wait for PostgreSQL ──────────────────────────────────────
echo "[1/3] Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT}..."
RETRIES=30
until pg_isready -h "$DB_HOST" -p "$DB_PORT" -q || [ $RETRIES -eq 0 ]; do
  echo "  Waiting... ($RETRIES retries left)"
  RETRIES=$((RETRIES - 1))
  sleep 1
done

if [ $RETRIES -eq 0 ]; then
  echo "ERROR: PostgreSQL not ready. Exiting."
  exit 1
fi
echo "  product_db is ready."

# ── 2. Run Alembic Migrations ───────────────────────────────────
echo "[2/3] Running migrations..."
if ls alembic/versions/*.py 1>/dev/null 2>&1; then
  alembic upgrade head
  echo "  Migrations complete."
else
  echo "  No migrations found — skipping."
fi

# ── 3. Start Application ────────────────────────────────────────
echo "[3/3] Starting application..."
echo "  Command: $@"
echo "──────────────────────────────────────────────"
exec "$@"

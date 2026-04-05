#!/bin/bash
# entrypoint.sh — notification_service
# ─────────────────────────────────────────────────────────────────────────────
# Steps:
#   1. Wait for PostgreSQL to be ready (pg_isready loop, max 30s)
#   2. Run Alembic migrations if versions exist, otherwise SQLModel create_all
#   3. Exec uvicorn (or whatever CMD is passed)
#
# Why this script:
#   Docker's depends_on health checks ensure the DB container is healthy, but
#   "healthy" only means pg_isready passed on the host. The DB may still need a
#   moment to accept connections from within the Docker network. This script
#   retries with a 1-second interval to eliminate "connection refused" errors
#   in fast-restart scenarios.
# ─────────────────────────────────────────────────────────────────────────────
set -e

echo "──────────────────────────────────────────────"
echo " notification_service — starting up"
echo "──────────────────────────────────────────────"

# ── Step 1: Wait for PostgreSQL ───────────────────────────────────────────────
echo "[1/3] Waiting for database..."
MAX_RETRIES=30
RETRIES=0
until pg_isready \
  -h "${NOTIFICATION_DB_HOST:-notification_db}" \
  -p "${DB_PORT:-5432}" \
  -U "${NOTIFICATION_DB_USER:-notif_admin}" \
  -q; do
  RETRIES=$((RETRIES + 1))
  if [ "$RETRIES" -ge "$MAX_RETRIES" ]; then
    echo "ERROR: Database did not become ready after ${MAX_RETRIES}s. Aborting."
    exit 1
  fi
  echo "  Database not ready — retrying in 1s (attempt ${RETRIES}/${MAX_RETRIES})..."
  sleep 1
done
echo "  Database is ready."

# ── Step 2: Migrations ────────────────────────────────────────────────────────
echo "[2/3] Running database migrations..."

# Check if alembic/versions has at least one .py migration file
if [ -d "alembic" ] && [ -d "alembic/versions" ] && \
   [ "$(ls alembic/versions/*.py 2>/dev/null | wc -l)" -gt 0 ]; then
  echo "  Running: alembic upgrade head"
  alembic upgrade head
  echo "  Migrations complete."
else
  echo "  No Alembic version files found — running SQLModel create_all (dev/staging mode)"
  python3 - << 'PYEOF'
import asyncio
from sqlmodel import SQLModel
from db.session import engine

# Import all models so SQLModel.metadata sees all five tables
from models.notification import (          # noqa: F401
    NotificationTemplate,
    Notification,
    NotificationDelivery,
    NotificationPreference,
    NotificationDevice,
)


async def create_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    print("  Tables created via SQLModel.metadata.create_all.")


asyncio.run(create_tables())
PYEOF
fi

# ── Step 3: Start application ─────────────────────────────────────────────────
echo "[3/3] Starting application..."
echo "  Command: $*"
echo "──────────────────────────────────────────────"
exec "$@"

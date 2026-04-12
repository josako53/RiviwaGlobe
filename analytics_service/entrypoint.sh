#!/bin/bash
# entrypoint.sh — analytics_service
# ─────────────────────────────────────────────────────────────────────────────
# Steps:
#   1. Wait for analytics_db PostgreSQL to be ready
#   2. Create tables via SQLModel.metadata.create_all (no Alembic)
#   3. Exec uvicorn
# ─────────────────────────────────────────────────────────────────────────────
set -e

echo "──────────────────────────────────────────────"
echo " analytics_service — starting up"
echo "──────────────────────────────────────────────"

# ── Step 1: Wait for analytics_db ────────────────────────────────────────────
echo "[1/3] Waiting for analytics_db..."
MAX_RETRIES=30
RETRIES=0
until pg_isready \
  -h "${ANALYTICS_DB_HOST:-analytics_db}" \
  -p "${ANALYTICS_DB_PORT:-5432}" \
  -U "${ANALYTICS_DB_USER:-analytics_admin}" \
  -q; do
  RETRIES=$((RETRIES + 1))
  if [ "$RETRIES" -ge "$MAX_RETRIES" ]; then
    echo "ERROR: analytics_db did not become ready after ${MAX_RETRIES}s. Aborting."
    exit 1
  fi
  echo "  analytics_db not ready — retrying in 1s (attempt ${RETRIES}/${MAX_RETRIES})..."
  sleep 1
done
echo "  analytics_db is ready."

# ── Step 2: Create tables ─────────────────────────────────────────────────────
echo "[2/3] Creating analytics_db tables..."
python3 - << 'PYEOF'
import asyncio
from sqlmodel import SQLModel
from db.session import analytics_engine

# Import all models so SQLModel.metadata sees all tables
from models.analytics import (  # noqa: F401
    StaffLogin,
    FeedbackSLAStatus,
    HotspotAlert,
    CommitteePerformance,
    FeedbackMLScore,
    GeneratedReport,
)


async def create():
    async with analytics_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    print("  analytics_db tables created/verified.")


asyncio.run(create())
PYEOF

# ── Step 3: Start application ─────────────────────────────────────────────────
echo "[3/3] Starting application..."
echo "  Command: $*"
echo "──────────────────────────────────────────────"
exec "$@"

#!/bin/bash
# entrypoint.sh — ai_service
set -e

echo "──────────────────────────────────────────────"
echo " ai_service — starting up"
echo "──────────────────────────────────────────────"

# ── Step 1: Wait for PostgreSQL ───────────────────────────────────────────────
echo "[1/3] Waiting for database..."
MAX_RETRIES=30
RETRIES=0
until pg_isready -h "${AI_DB_HOST:-ai_db}" -p "${DB_PORT:-5432}" -U "${AI_DB_USER:-ai_admin}" -q; do
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
if [ -d "alembic" ] && [ -d "alembic/versions" ] && [ "$(ls -A alembic/versions 2>/dev/null)" ]; then
  echo "  Running: alembic upgrade head"
  alembic upgrade head
  echo "  Migrations complete."
else
  echo "  No Alembic versions found — running SQLModel create_all (dev mode)"
  python3 - << 'PYEOF'
import asyncio
from sqlmodel import SQLModel
from db.session import engine
from models.conversation import AIConversation, ProjectKnowledgeBase, StakeholderCache  # noqa

async def create():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    print("  Tables created via create_all.")

asyncio.run(create())
PYEOF
fi

# ── Step 3: Start application ─────────────────────────────────────────────────
echo "[3/3] Starting application..."
exec "$@"

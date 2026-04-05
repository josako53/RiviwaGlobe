#!/bin/bash
# entrypoint.sh — feedback_service
# ─────────────────────────────────────────────────────────────────────────────
# Steps:
#   1. Wait for PostgreSQL to be ready
#   2. Run Alembic migrations if versions exist, otherwise run create_all
#   3. Exec uvicorn
# ─────────────────────────────────────────────────────────────────────────────
set -e

echo "──────────────────────────────────────────────"
echo " feedback_service — starting up"
echo "──────────────────────────────────────────────"

# ── Step 1: Wait for PostgreSQL ───────────────────────────────────────────────
echo "[1/3] Waiting for database..."
MAX_RETRIES=30
RETRIES=0
until pg_isready -h "${FEEDBACK_DB_HOST:-feedback_db}" -p "${DB_PORT:-5432}" -U "${FEEDBACK_DB_USER:-feedback_admin}" -q; do
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

# Check if alembic directory and versions folder exist with at least one migration
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

# Import all models so SQLModel.metadata sees all tables
from models.feedback import (                                      # noqa
    Feedback, FeedbackAction, FeedbackEscalation, FeedbackResolution,
    FeedbackAppeal, GrievanceCommittee, GrievanceCommitteeMember,
    FeedbackCategoryDef, ChannelSession, EscalationRequest,
)
from models.project import ProjectCache, ProjectStageCache          # noqa

async def create():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    print("  Tables created via create_all.")

asyncio.run(create())
PYEOF
fi

# ── Step 3: Start application ─────────────────────────────────────────────────
echo "[3/3] Starting application..."
echo "  Command: $*"
echo "──────────────────────────────────────────────"
exec "$@"

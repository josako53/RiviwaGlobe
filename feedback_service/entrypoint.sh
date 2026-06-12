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

# ── Step 2: Database init + migrations ───────────────────────────────────────
# On a fresh database the initial migration is intentionally empty.
# If no alembic_version table exists we create all tables first, stamp at
# head, then skip running migrations (tables already exist).
echo "[2/3] Running database migrations..."
python3 - << 'PYEOF'
import sys, os
APP_DIR = "/app/feedback_service"
sys.path.insert(0, APP_DIR)
from core.config import settings
from sqlalchemy import create_engine, inspect

db_url = str(settings.DATABASE_URL).replace('+asyncpg', '+psycopg').replace('postgresql+asyncpg', 'postgresql+psycopg') \
    if not hasattr(settings, 'SYNC_DATABASE_URL') else settings.SYNC_DATABASE_URL
engine = create_engine(db_url)
insp   = inspect(engine)

if "alembic_version" not in insp.get_table_names():
    from sqlmodel import SQLModel
    from models.feedback import (
        Feedback, FeedbackAction, FeedbackEscalation, FeedbackResolution,
        FeedbackAppeal, GrievanceCommittee, GrievanceCommitteeMember,
        FeedbackCategoryDef, ChannelSession, EscalationRequest,
    )
    from models.project import ProjectCache, ProjectStageCache
    from models.employee_feedback import EmployeeFeedback
    from models.escalation import EscalationPath, EscalationLevel
    SQLModel.metadata.create_all(engine, checkfirst=True)
    from alembic.config import Config
    from alembic import command as alembic_cmd
    cfg = Config(os.path.join(APP_DIR, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(APP_DIR, "alembic"))
    alembic_cmd.stamp(cfg, "head")
    print("Fresh database: all tables created, stamped at head.")
else:
    from alembic.config import Config
    from alembic import command as alembic_cmd
    cfg = Config(os.path.join(APP_DIR, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(APP_DIR, "alembic"))
    alembic_cmd.upgrade(cfg, "head")
    print("Existing database: migrations applied.")
PYEOF
echo "  Migrations complete."

# ── Step 3: Start application ─────────────────────────────────────────────────
echo "[3/3] Starting application..."
echo "  Command: $*"
echo "──────────────────────────────────────────────"
exec "$@"

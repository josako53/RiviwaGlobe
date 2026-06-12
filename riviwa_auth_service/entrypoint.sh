#!/bin/bash
# entrypoint.sh
# ─────────────────────────────────────────────────────────────────────────────
# Container entry point for riviwa_auth_service.
#
# Runs on every `docker compose up` — both dev and production.
#
# Steps
# ──────
#   1. Wait for the DB to accept connections (belt-and-suspenders on top of
#      the Docker healthcheck — handles transient TCP resets after healthcheck
#      passes but before PostgreSQL is fully ready for queries).
#   2. Run all pending Alembic migrations (idempotent — safe to run on restart).
#   3. Exec the command passed to the container (uvicorn).
#      · Production : CMD in Dockerfile  → uvicorn without --reload
#      · Development: `command:` in docker-compose.override.yml → uvicorn --reload
#
# Usage
# ──────
#   Automatically called by Docker via ENTRYPOINT.
#   Do NOT invoke uvicorn directly — always go through this script.
# ─────────────────────────────────────────────────────────────────────────────

set -e  # abort on any error

echo "──────────────────────────────────────────────"
echo " riviwa_auth_service — starting up"
echo "──────────────────────────────────────────────"

# ── Step 1: Wait for PostgreSQL ───────────────────────────────────────────────
# pg_isready exits 0 only when the server is accepting connections.
# Retry up to 30 times (30 s total) before giving up.
echo "[1/3] Waiting for database..."
MAX_RETRIES=30
RETRIES=0
until pg_isready -h "${AUTH_DB_HOST:-riviwa_auth_db}" -p "${DB_PORT:-5432}" -U "${AUTH_DB_USER:-riviwa_auth_admin}" -q; do
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
# On a fresh database the initial_schema.py migration is intentionally empty
# (the schema was originally bootstrapped via SQLModel.metadata.create_all).
# If no alembic_version table exists we create all tables first, then stamp
# at head so Alembic knows every migration has been accounted for.
# On an existing database we run upgrade head normally (idempotent).
echo "[2/3] Running database migrations..."
python3 - << 'PYEOF'
import sys, os
APP_DIR = "/app/riviwa_auth_service"
sys.path.insert(0, APP_DIR)
from core.config import settings
from sqlalchemy import create_engine, inspect

engine = create_engine(settings.SYNC_DATABASE_URL)
insp   = inspect(engine)

if "alembic_version" not in insp.get_table_names():
    from sqlmodel import SQLModel
    import db.base  # registers all models into SQLModel.metadata
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

# ── Step 3: Start the application ────────────────────────────────────────────
# `exec` replaces this shell with the uvicorn process so that:
#   · PID 1 is uvicorn (correct signal handling — SIGTERM stops the server)
#   · Docker logs stream directly from uvicorn (no shell buffering)
echo "[3/3] Starting application..."
echo "  Command: $*"
echo "──────────────────────────────────────────────"
exec "$@"

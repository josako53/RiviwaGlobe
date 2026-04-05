#!/usr/bin/env bash
set -euo pipefail

SERVICE="recommendation_service"

log() { echo "$(date -Iseconds) | $*"; }

log "──────────────────────────────────────────────"
log " ${SERVICE} — starting up"
log "──────────────────────────────────────────────"

# ── 1. Wait for PostgreSQL ────────────────────────────────────────────────────
log "[1/3] Waiting for database..."
until python -c "
import psycopg, os, sys
try:
    psycopg.connect(
        host=os.getenv('RECOMMENDATION_DB_HOST', 'recommendation_db'),
        port=int(os.getenv('DB_PORT', 5432)),
        dbname=os.getenv('RECOMMENDATION_DB_NAME', 'recommendation_db'),
        user=os.getenv('RECOMMENDATION_DB_USER', 'rec_admin'),
        password=os.getenv('RECOMMENDATION_DB_PASSWORD', 'rec_pass_321'),
        connect_timeout=3,
    ).close()
    sys.exit(0)
except Exception:
    sys.exit(1)
" 2>/dev/null; do
    sleep 2
done
log "  Database is ready."

# ── 2. Create tables (via SQLModel metadata.create_all in lifespan) ──────────
log "[2/3] Tables will be created by the application lifespan handler."

# ── 3. Start application ─────────────────────────────────────────────────────
log "[3/3] Starting application..."
CMD="uvicorn main:app --host 0.0.0.0 --port 8055"

if [ "${ENVIRONMENT:-production}" != "production" ]; then
    CMD="${CMD} --reload --reload-dir /app/recommendation_service"
fi

log "  Command: ${CMD}"
log "──────────────────────────────────────────────"
exec ${CMD}

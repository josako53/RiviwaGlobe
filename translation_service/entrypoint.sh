#!/usr/bin/env bash
# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  translation_service  |  Port: 8050  |  DB: translation_db (5438)
# FILE     :  entrypoint.sh
# ───────────────────────────────────────────────────────────────────────────
set -euo pipefail

SERVICE="translation_service"

log() { echo "$(date -Iseconds) | $*"; }

log "──────────────────────────────────────────────"
log " ${SERVICE} — starting up"
log "──────────────────────────────────────────────"

# ── 1. Wait for PostgreSQL ────────────────────────────────────────────────────
log "[1/4] Waiting for database..."
until python -c "
import psycopg, os, sys
try:
    psycopg.connect(
        host=os.getenv('TRANSLATION_DB_HOST', 'translation_db'),
        port=int(os.getenv('DB_PORT', 5432)),
        dbname=os.getenv('TRANSLATION_DB_NAME', 'translation_db'),
        user=os.getenv('TRANSLATION_DB_USER', 'trans_admin'),
        password=os.getenv('TRANSLATION_DB_PASSWORD', 'trans_pass_321'),
        connect_timeout=3,
    ).close()
    sys.exit(0)
except Exception:
    sys.exit(1)
" 2>/dev/null; do
    sleep 2
done
log "  Database is ready."

# ── 2. Run Alembic migrations ─────────────────────────────────────────────────
log "[2/4] Running database migrations..."
if find alembic/versions -name "*.py" 2>/dev/null | grep -q .; then
    alembic upgrade head
    log "  Alembic migrations applied."
else
    python - <<'PYEOF'
import asyncio
from db.session import engine
from db.base import Base
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
asyncio.run(create_tables())
PYEOF
    log "  Tables created via metadata.create_all (no migration files)."
fi

# ── 3. Download NLLB-200 model (if enabled) ───────────────────────────────────
log "[3/4] Checking NLLB-200 model..."
NLLB_ENABLED="${NLLB_ENABLED:-true}"
if [ "${NLLB_ENABLED}" = "true" ]; then
    python download_model.py
else
    log "  NLLB_ENABLED=false — skipping model download."
fi

# ── 4. Start application ──────────────────────────────────────────────────────
log "[4/4] Starting application..."
CMD="uvicorn main:app --host 0.0.0.0 --port 8050"

if [ "${ENVIRONMENT:-production}" != "production" ]; then
    CMD="${CMD} --reload --reload-dir /app/translation_service"
fi

log "  Command: ${CMD}"
log "──────────────────────────────────────────────"
exec ${CMD}

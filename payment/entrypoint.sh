#!/bin/sh
set -e

echo "[payment_service] Waiting for database..."
until python3 -c "
import asyncio, asyncpg, os
async def check():
    url = os.environ.get('DATABASE_URL','')
    if '+asyncpg' in url:
        url = url.replace('postgresql+asyncpg','postgresql')
    await asyncpg.connect(url)
asyncio.run(check())
" 2>/dev/null; do
  echo "[payment_service] DB not ready, retrying in 2s..."
  sleep 2
done

echo "[payment_service] Running Alembic migrations..."
alembic upgrade head || echo "[payment_service] Alembic not configured, using SQLModel create_all"

echo "[payment_service] Starting server on port 8040..."
exec uvicorn main:app --host 0.0.0.0 --port 8040 --workers 2 --loop uvloop

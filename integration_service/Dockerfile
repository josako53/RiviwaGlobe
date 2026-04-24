# ── Builder ───────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

RUN pip install uv
WORKDIR /app
COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

# ── Runtime ───────────────────────────────────────────────────────────────────
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Non-root user (matches other Riviwa services)
RUN useradd -m -u 1000 josako

WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY . .
RUN chown -R josako:josako /app

USER josako

EXPOSE 8100

ENTRYPOINT ["./entrypoint.sh"]

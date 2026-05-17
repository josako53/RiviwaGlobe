FROM python:3.11-slim AS builder
RUN pip install uv
WORKDIR /build
COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt --target /opt/venv

FROM python:3.11-slim AS runtime
RUN apt-get update && apt-get install -y --no-install-recommends postgresql-client && rm -rf /var/lib/apt/lists/*
RUN useradd -m -u 1000 josako
WORKDIR /app/subscription_service
COPY --from=builder /opt/venv /opt/venv
COPY . .
ENV PYTHONPATH=/app/subscription_service:/opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN chmod +x entrypoint.sh
USER josako
EXPOSE 8140
ENTRYPOINT ["./entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8140", "--workers", "2", "--loop", "uvloop"]

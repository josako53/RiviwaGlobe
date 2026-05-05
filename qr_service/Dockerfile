FROM python:3.11-slim AS builder
RUN pip install uv
WORKDIR /build
COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt --target /opt/venv

FROM python:3.11-slim AS runtime
RUN apt-get update && apt-get install -y --no-install-recommends postgresql-client && rm -rf /var/lib/apt/lists/*
RUN useradd -m -u 1000 josako
WORKDIR /app/qr_service
COPY --from=builder /opt/venv /opt/venv
COPY . .
ENV PYTHONPATH=/app/qr_service:/opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN chmod +x entrypoint.sh
USER josako
EXPOSE 8120
ENTRYPOINT ["./entrypoint.sh"]

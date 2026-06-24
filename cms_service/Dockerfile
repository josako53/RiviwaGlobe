FROM python:3.11-slim AS builder

RUN pip install uv
WORKDIR /app/cms_service
COPY requirements.txt .
RUN uv pip install --system --target /opt/venv -r requirements.txt

FROM python:3.11-slim AS final

RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r josako && useradd -r -g josako josako

COPY --from=builder /opt/venv /opt/venv
ENV PYTHONPATH=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app/cms_service
COPY . .

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

RUN chown -R josako:josako /app
USER josako

EXPOSE 8150

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8150"]

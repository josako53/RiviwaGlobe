FROM python:3.11-slim AS builder
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app/ai_service
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        git \
    && rm -rf /var/lib/apt/lists/*
RUN pip install uv
RUN uv venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
COPY requirements.txt .
RUN uv pip install --no-cache --index-strategy unsafe-best-match -r requirements.txt

FROM python:3.11-slim
RUN groupadd -r josako && useradd -r -g josako josako
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq-dev \
        postgresql-client \
    && rm -rf /var/lib/apt/lists/*
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"
WORKDIR /app/ai_service
COPY --from=builder /opt/venv /opt/venv
COPY . /app/ai_service
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
RUN mkdir -p /models/sentence-transformers /home/josako/.cache && \
    chown -R josako:josako /app /entrypoint.sh /models /home/josako
ENV HF_HOME=/models/sentence-transformers
ENV TRANSFORMERS_CACHE=/models/sentence-transformers
ENV SENTENCE_TRANSFORMERS_HOME=/models/sentence-transformers
USER josako
EXPOSE 8085
ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8085"]

# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  translation_service  |  Port: 8050  |  DB: translation_db (5438)
# FILE     :  Dockerfile
# ───────────────────────────────────────────────────────────────────────────
#
# Build notes
# ───────────────────────────────────────────────────────────────────────────
# · PyTorch + Transformers require native build tools and are large.
#   We use a multi-stage build to keep the final image lean.
#
# · The NLLB-200 model weights are NOT baked into the image.
#   They are mounted at runtime via a Docker volume:
#     - Path inside container : /models/nllb   (NLLB_MODEL_DIR default)
#     - Host path             : ./models/nllb  (set in docker-compose.yml)
#   On first startup, entrypoint.sh runs download_model.py which downloads
#   the model to the mounted volume path. Subsequent starts skip the download.
#
# · GPU support: replace torch==2.7.0 with torch==2.7.0+cu124 (CUDA 12.4)
#   in requirements.txt and set NLLB_DEVICE=cuda in .env
# ───────────────────────────────────────────────────────────────────────────

# ── Stage 1: dependency builder ───────────────────────────────────────────────
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app/translation_service

# Build tools needed for sentencepiece and some torch extensions
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
# --no-build-isolation for PyTorch wheels which use pre-built binaries
RUN uv pip install --no-cache -r requirements.txt

# ── Stage 2: runtime image ────────────────────────────────────────────────────
FROM python:3.11-slim

RUN groupadd -r josako && useradd -r -g josako josako

# psycopg (used in entrypoint DB check) needs libpq
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app/translation_service

COPY --from=builder /opt/venv /opt/venv
COPY . /app/translation_service
COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

# /models/nllb is where the NLLB weights are mounted at runtime.
# Create it here so Docker doesn't fail if the host bind mount is missing.
RUN mkdir -p /models/nllb && chown -R josako:josako /app /entrypoint.sh /models

USER josako

EXPOSE 8050

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8050"]

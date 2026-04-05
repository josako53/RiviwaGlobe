#!/usr/bin/env python3
# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  translation_service  |  Port: 8050  |  DB: translation_db (5438)
# FILE     :  download_model.py
# ───────────────────────────────────────────────────────────────────────────
"""
download_model.py — One-shot NLLB-200 model download script.

Run at container startup (before uvicorn):
  python download_model.py

The script checks if the model is already present before downloading.
Safe to call on every container start — skips download if complete.

Environment variables read:
  NLLB_ENABLED     — if "false", exits immediately (skip download)
  NLLB_MODEL_NAME  — HuggingFace model ID  (default: facebook/nllb-200-distilled-1.3B)
  NLLB_MODEL_DIR   — local path to save to (default: /models/nllb)

Download size:
  nllb-200-distilled-600M  →  ~2.5 GB
  nllb-200-distilled-1.3B  →  ~5.0 GB   ← default
  nllb-200-1.3B            →  ~5.0 GB
"""
import os
import sys
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [download_model] %(levelname)s %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger(__name__)


def main() -> None:
    # ── Read config from environment ──────────────────────────────────────────
    enabled    = os.getenv("NLLB_ENABLED", "true").lower()
    model_name = os.getenv("NLLB_MODEL_NAME", "facebook/nllb-200-distilled-1.3B")
    model_dir  = os.getenv("NLLB_MODEL_DIR", "/models/nllb")

    if enabled in ("false", "0", "no"):
        log.info("NLLB_ENABLED=false — skipping model download.")
        sys.exit(0)

    marker = Path(model_dir) / ".download_complete"
    if marker.exists():
        stored = marker.read_text().strip()
        if stored == model_name:
            log.info("Model already downloaded: %s at %s", model_name, model_dir)
            sys.exit(0)
        else:
            log.info(
                "Model name changed (%s → %s) — re-downloading.",
                stored, model_name,
            )

    log.info("Starting download: %s → %s", model_name, model_dir)

    try:
        from providers.nllb import download_model
    except ImportError:
        # Run without the app on sys.path — add translation_service root
        sys.path.insert(0, str(Path(__file__).parent))
        from providers.nllb import download_model

    try:
        download_model(model_name, model_dir)
        log.info("Download complete.")
    except Exception as exc:
        log.error("Download failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()

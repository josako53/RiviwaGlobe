# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  translation_service  |  Port: 8050  |  DB: translation_db (5438)
# FILE     :  providers/nllb.py
# ───────────────────────────────────────────────────────────────────────────
"""
providers/nllb.py — Meta NLLB-200 local inference provider.

Model
─────
  facebook/nllb-200-distilled-1.3B  (default — best quality/speed trade-off)
  facebook/nllb-200-distilled-600M  (lighter — faster on CPU-only setups)
  facebook/nllb-200-1.3B            (full quality — needs more RAM)

The model is downloaded once to NLLB_MODEL_DIR on first startup (or when
`download_model()` is called explicitly from the entrypoint), then loaded into
memory.  All subsequent requests are served locally with zero external calls.

Language codes
──────────────
NLLB uses FLORES-200 codes, not BCP-47:
  sw  → swh_Latn   (Swahili)
  en  → eng_Latn   (English)
  fr  → fra_Latn   (French)
  ar  → arb_Arab   (Arabic)
  sw  → swh_Latn   (Swahili — Tanzania primary)
  … see BCP47_TO_FLORES below for full mapping.

Design
──────
  · Model is loaded once at process start via NLLBProvider.load().
  · A singleton _model_state dict holds the loaded tokenizer + pipeline.
  · translate() and translate_batch() are async — CPU inference runs in a
    ThreadPoolExecutor so the async event loop is never blocked.
  · Long texts are chunked at sentence boundaries to stay within the 512-
    token context window.
  · translate_batch() processes each text independently (no batching at the
    model level — keeps memory predictable on 4 GB RAM containers).
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

import structlog

from core.config import settings
from core.exceptions import TranslationFailedError
from providers.base import BaseTranslationProvider, TranslationResult

log = structlog.get_logger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# FLORES-200 ↔ BCP-47 language code mapping
# Extended for all languages Riviwa may encounter
# ─────────────────────────────────────────────────────────────────────────────

BCP47_TO_FLORES: dict[str, str] = {
    # ── East African ──────────────────────────────────────────────────────────
    "sw":  "swh_Latn",   # Swahili (Tanzania / Kenya)
    "am":  "amh_Ethi",   # Amharic
    "so":  "som_Latn",   # Somali
    "om":  "gaz_Latn",   # Oromo
    "ti":  "tir_Ethi",   # Tigrinya
    "rw":  "kin_Latn",   # Kinyarwanda
    "rn":  "run_Latn",   # Rundi
    "ny":  "nya_Latn",   # Chichewa / Nyanja (Malawi)
    "mg":  "plt_Latn",   # Malagasy
    # ── West African ──────────────────────────────────────────────────────────
    "ha":  "hau_Latn",   # Hausa
    "yo":  "yor_Latn",   # Yoruba
    "ig":  "ibo_Latn",   # Igbo
    "ak":  "aka_Latn",   # Akan / Twi
    "ee":  "ewe_Latn",   # Ewe
    "lg":  "lug_Latn",   # Luganda
    "ln":  "lin_Latn",   # Lingala
    "sg":  "sag_Latn",   # Sango
    "bm":  "bam_Latn",   # Bambara
    # ── Southern African ──────────────────────────────────────────────────────
    "zu":  "zul_Latn",   # Zulu
    "xh":  "xho_Latn",   # Xhosa
    "st":  "sot_Latn",   # Sesotho
    "tn":  "tsn_Latn",   # Setswana
    "sn":  "sna_Latn",   # Shona
    "af":  "afr_Latn",   # Afrikaans
    # ── European ──────────────────────────────────────────────────────────────
    "en":  "eng_Latn",   # English
    "fr":  "fra_Latn",   # French
    "de":  "deu_Latn",   # German
    "es":  "spa_Latn",   # Spanish
    "pt":  "por_Latn",   # Portuguese
    "it":  "ita_Latn",   # Italian
    "nl":  "nld_Latn",   # Dutch
    "pl":  "pol_Latn",   # Polish
    "ru":  "rus_Cyrl",   # Russian
    "uk":  "ukr_Cyrl",   # Ukrainian
    "cs":  "ces_Latn",   # Czech
    "ro":  "ron_Latn",   # Romanian
    "hu":  "hun_Latn",   # Hungarian
    "el":  "ell_Grek",   # Greek
    "sv":  "swe_Latn",   # Swedish
    "da":  "dan_Latn",   # Danish
    "fi":  "fin_Latn",   # Finnish
    "no":  "nob_Latn",   # Norwegian
    "tr":  "tur_Latn",   # Turkish
    # ── Middle East / RTL ─────────────────────────────────────────────────────
    "ar":  "arb_Arab",   # Arabic (Modern Standard)
    "fa":  "pes_Arab",   # Persian / Farsi
    "ur":  "urd_Arab",   # Urdu
    "he":  "heb_Hebr",   # Hebrew
    # ── South / Southeast Asian ───────────────────────────────────────────────
    "hi":  "hin_Deva",   # Hindi
    "bn":  "ben_Beng",   # Bengali
    "ta":  "tam_Taml",   # Tamil
    "te":  "tel_Telu",   # Telugu
    "ml":  "mal_Mlym",   # Malayalam
    "kn":  "kan_Knda",   # Kannada
    "si":  "sin_Sinh",   # Sinhala
    "th":  "tha_Thai",   # Thai
    "id":  "ind_Latn",   # Indonesian
    "ms":  "zsm_Latn",   # Malay
    "vi":  "vie_Latn",   # Vietnamese
    "tl":  "tgl_Latn",   # Filipino / Tagalog
    # ── East Asian ────────────────────────────────────────────────────────────
    "zh":  "zho_Hans",   # Chinese (Simplified)
    "zh-tw": "zho_Hant", # Chinese (Traditional)
    "ja":  "jpn_Jpan",   # Japanese
    "ko":  "kor_Hang",   # Korean
    # ── Other ─────────────────────────────────────────────────────────────────
    "ka":  "kat_Geor",   # Georgian
    "hy":  "hye_Armn",   # Armenian
    "az":  "azj_Latn",   # Azerbaijani
}

# Reverse mapping for converting FLORES codes back to BCP-47
FLORES_TO_BCP47: dict[str, str] = {v: k for k, v in BCP47_TO_FLORES.items()}

# Maximum tokens per chunk — NLLB context window is 512, leave headroom
_MAX_CHUNK_TOKENS = 400
# Approximate chars per token for most Latin-script languages
_CHARS_PER_TOKEN  = 4

# Thread pool for CPU-bound inference
_executor = ThreadPoolExecutor(max_workers=int(os.getenv("NLLB_WORKERS", "2")))

# ─────────────────────────────────────────────────────────────────────────────
# Singleton model state  (loaded once per process)
# ─────────────────────────────────────────────────────────────────────────────

_model_state: dict = {
    "tokenizer": None,
    "model":     None,
    "loaded":    False,
    "load_error": None,
}


def _bcp47_to_flores(code: str) -> str:
    """
    Convert BCP-47 code to FLORES-200.
    Strips region subtag before lookup: 'sw-TZ' → 'sw' → 'swh_Latn'.
    Raises ValueError if not found.
    """
    normalised = code.lower().replace("_", "-").split("-")[0]
    # Try full code first (e.g. 'zh-tw'), then stripped
    flores = BCP47_TO_FLORES.get(code.lower()) or BCP47_TO_FLORES.get(normalised)
    if not flores:
        raise ValueError(
            f"Language '{code}' is not supported by NLLB-200. "
            f"Supported codes: {sorted(BCP47_TO_FLORES.keys())}"
        )
    return flores


def _chunk_text(text: str) -> list[str]:
    """
    Split long text into chunks that fit within NLLB's 512-token window.
    Splits on sentence boundaries (. ! ? \n) first, then hard-splits if a
    single sentence still exceeds the limit.
    """
    max_chars = _MAX_CHUNK_TOKENS * _CHARS_PER_TOKEN

    if len(text) <= max_chars:
        return [text]

    # Split on sentence boundaries
    sentences = re.split(r"(?<=[.!?\n])\s+", text.strip())
    chunks: list[str] = []
    current = ""

    for sentence in sentences:
        if len(current) + len(sentence) + 1 <= max_chars:
            current = (current + " " + sentence).strip()
        else:
            if current:
                chunks.append(current)
            # If the single sentence is still too long, hard-split it
            if len(sentence) > max_chars:
                for i in range(0, len(sentence), max_chars):
                    chunks.append(sentence[i:i + max_chars])
                current = ""
            else:
                current = sentence

    if current:
        chunks.append(current)

    return chunks


def _do_translate_sync(
    text: str,
    src_flores: str,
    tgt_flores: str,
) -> str:
    """
    Synchronous NLLB inference — runs in ThreadPoolExecutor.
    Chunks long texts and joins translated chunks with spaces.
    """
    tokenizer = _model_state["tokenizer"]
    model     = _model_state["model"]

    chunks     = _chunk_text(text)
    translated = []

    for chunk in chunks:
        inputs = tokenizer(
            chunk,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512,
        )
        tgt_lang_id = tokenizer.convert_tokens_to_ids(tgt_flores)
        output_ids  = model.generate(
            **inputs,
            forced_bos_token_id=tgt_lang_id,
            max_new_tokens=512,
            num_beams=4,
            early_stopping=True,
        )
        decoded = tokenizer.batch_decode(output_ids, skip_special_tokens=True)
        translated.extend(decoded)

    return " ".join(translated)


# ─────────────────────────────────────────────────────────────────────────────
# Model download utility  (called from entrypoint.sh or download_model.py)
# ─────────────────────────────────────────────────────────────────────────────

def download_model(model_name: str, model_dir: str) -> None:
    """
    Download NLLB model from HuggingFace Hub to model_dir.
    Safe to call multiple times — skips download if already present.
    Intended to be called at container startup before the API starts.
    """
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    model_path = Path(model_dir)
    marker     = model_path / ".download_complete"

    if marker.exists():
        log.info("nllb.model_already_downloaded", path=str(model_path))
        return

    log.info("nllb.downloading_model", model=model_name, dest=str(model_path))
    model_path.mkdir(parents=True, exist_ok=True)

    # Download tokenizer
    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        cache_dir=str(model_path),
    )
    tokenizer.save_pretrained(str(model_path))
    log.info("nllb.tokenizer_saved")

    # Download model weights
    model = AutoModelForSeq2SeqLM.from_pretrained(
        model_name,
        cache_dir=str(model_path),
    )
    model.save_pretrained(str(model_path))
    log.info("nllb.model_saved")

    # Write completion marker so we skip on next start
    marker.write_text(model_name)
    log.info("nllb.download_complete", model=model_name)


# ─────────────────────────────────────────────────────────────────────────────
# Provider
# ─────────────────────────────────────────────────────────────────────────────

class NLLBProvider(BaseTranslationProvider):
    """
    Meta NLLB-200 local inference provider.

    Loads the model from NLLB_MODEL_DIR (must be pre-downloaded).
    Falls back gracefully if the model directory doesn't exist or the
    transformers package is not installed.
    """

    @property
    def name(self) -> str:
        return "nllb"

    def is_configured(self) -> bool:
        """True if the model directory exists and contains model files."""
        model_dir = settings.NLLB_MODEL_DIR
        if not model_dir:
            return False
        path   = Path(model_dir)
        marker = path / ".download_complete"
        return marker.exists()

    def load(self) -> None:
        """
        Load tokenizer + model into memory.
        Called once at application startup via lifespan.
        Thread-safe — idempotent if called multiple times.
        """
        if _model_state["loaded"]:
            return
        if _model_state["load_error"]:
            raise RuntimeError(_model_state["load_error"])

        try:
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        except ImportError as exc:
            msg = "transformers not installed. Add transformers + torch to requirements.txt."
            _model_state["load_error"] = msg
            raise RuntimeError(msg) from exc

        model_dir = settings.NLLB_MODEL_DIR
        log.info("nllb.loading_model", path=model_dir)

        try:
            tokenizer = AutoTokenizer.from_pretrained(model_dir)
            model     = AutoModelForSeq2SeqLM.from_pretrained(model_dir)

            # Move to GPU if available
            try:
                import torch
                if torch.cuda.is_available():
                    model = model.cuda()
                    log.info("nllb.using_gpu")
                else:
                    log.info("nllb.using_cpu")
            except ImportError:
                log.info("nllb.torch_not_found_using_cpu")

            model.eval()

            _model_state["tokenizer"] = tokenizer
            _model_state["model"]     = model
            _model_state["loaded"]    = True
            log.info("nllb.model_ready", model=settings.NLLB_MODEL_NAME)

        except Exception as exc:
            _model_state["load_error"] = str(exc)
            log.error("nllb.load_failed", error=str(exc))
            raise

    async def translate(
        self,
        text:            str,
        target_language: str,
        source_language: Optional[str] = None,
    ) -> TranslationResult:
        if not _model_state["loaded"]:
            raise TranslationFailedError("NLLB model is not loaded.")

        try:
            src_flores = _bcp47_to_flores(source_language or settings.DEFAULT_LANGUAGE)
            tgt_flores = _bcp47_to_flores(target_language)
        except ValueError as exc:
            raise TranslationFailedError(str(exc)) from exc

        # Set tokenizer src lang before encode
        _model_state["tokenizer"].src_lang = src_flores

        loop   = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                _executor,
                _do_translate_sync,
                text,
                src_flores,
                tgt_flores,
            )
        except Exception as exc:
            log.error("nllb.inference_failed", error=str(exc))
            raise TranslationFailedError(f"NLLB inference error: {exc}") from exc

        # Convert FLORES code back to BCP-47 for the response
        src_bcp47 = FLORES_TO_BCP47.get(src_flores, source_language or settings.DEFAULT_LANGUAGE)

        return TranslationResult(
            translated_text=result,
            source_language=src_bcp47,
            provider="nllb",
        )

    async def translate_batch(
        self,
        texts:           list[str],
        target_language: str,
        source_language: Optional[str] = None,
    ) -> list[TranslationResult]:
        """Translate each text independently (predictable memory usage)."""
        results = []
        for text in texts:
            result = await self.translate(text, target_language, source_language)
            results.append(result)
        return results

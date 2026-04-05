# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  translation_service  |  Port: 8050  |  DB: translation_db (5438)
# FILE     :  providers/base.py
# ───────────────────────────────────────────────────────────────────────────
"""providers/base.py — Abstract base class for translation providers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class TranslationResult:
    __slots__ = ("translated_text", "source_language", "provider")

    def __init__(self, translated_text: str, source_language: str, provider: str) -> None:
        self.translated_text = translated_text
        self.source_language = source_language
        self.provider        = provider


class BaseTranslationProvider(ABC):
    """
    All translation backends implement this interface.
    Services depend only on this abstraction — swapping Google → DeepL
    requires no changes outside providers/.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier string: 'google' | 'deepl' | 'libre'"""

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True if all required env vars / credentials are present."""

    @abstractmethod
    async def translate(
        self,
        text:            str,
        target_language: str,
        source_language: Optional[str] = None,
    ) -> TranslationResult:
        """
        Translate text to target_language.
        source_language=None → auto-detect by provider.
        Raises TranslationFailedError on provider error.
        """

    @abstractmethod
    async def translate_batch(
        self,
        texts:           list[str],
        target_language: str,
        source_language: Optional[str] = None,
    ) -> list[TranslationResult]:
        """Translate a batch of strings to the same target language."""


class DetectionResult:
    """Result of a provider-side language detection call."""
    __slots__ = ("detected_language", "confidence", "provider", "alternatives")

    def __init__(
        self,
        detected_language: str,
        confidence:        float,
        provider:          str,
        alternatives:      list | None = None,
    ) -> None:
        self.detected_language = detected_language
        self.confidence        = confidence
        self.provider          = provider
        self.alternatives      = alternatives or []

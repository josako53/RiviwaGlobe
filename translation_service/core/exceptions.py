# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  translation_service  |  Port: 8050  |  DB: translation_db (5438)
# FILE     :  core/exceptions.py
# ───────────────────────────────────────────────────────────────────────────
"""core/exceptions.py — Domain exceptions for translation_service."""
from __future__ import annotations

from typing import Any, Optional
from fastapi import status


class AppError(Exception):
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code:  str = "INTERNAL_ERROR"
    message:     str = "An unexpected error occurred."

    def __init__(
        self,
        message:     Optional[str]            = None,
        detail:      Optional[dict[str, Any]] = None,
        *,
        error_code:  Optional[str] = None,
        status_code: Optional[int] = None,
    ) -> None:
        self.message     = message     or self.__class__.message
        self.detail:     dict[str, Any] = detail or {}
        self.error_code  = error_code  or self.__class__.error_code
        self.status_code = status_code or self.__class__.status_code
        super().__init__(self.message)

    def to_response_body(self) -> dict[str, Any]:
        body: dict[str, Any] = {"error": self.error_code, "message": self.message}
        if self.detail:
            body["detail"] = self.detail
        return body


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code  = "NOT_FOUND"
    message     = "The requested resource was not found."


class ValidationError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code  = "VALIDATION_ERROR"
    message     = "Request validation failed."


class UnauthorisedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code  = "UNAUTHORISED"
    message     = "Authentication required."


class LanguageNotSupportedError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code  = "LANGUAGE_NOT_SUPPORTED"
    message     = "The requested language is not supported."


class LanguagePreferenceNotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code  = "PREFERENCE_NOT_FOUND"
    message     = "No language preference found for this user."


class DetectionFailedError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code  = "DETECTION_FAILED"
    message     = "Language could not be detected from the provided text."


class TranslationFailedError(AppError):
    status_code = status.HTTP_502_BAD_GATEWAY
    error_code  = "TRANSLATION_FAILED"
    message     = "Translation provider returned an error."


class ProviderNotConfiguredError(AppError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    error_code  = "PROVIDER_NOT_CONFIGURED"
    message     = "No translation provider is configured. Set TRANSLATION_PROVIDER and API keys."

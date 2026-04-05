"""core/exceptions.py — Recommendation service exceptions."""
from __future__ import annotations

from fastapi import status


class AppError(Exception):
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "INTERNAL_ERROR"
    message: str = "An unexpected error occurred."

    def __init__(self, message: str | None = None):
        self.message = message or self.__class__.message
        super().__init__(self.message)


class EntityNotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "ENTITY_NOT_FOUND"
    message = "The requested entity was not found in the recommendation index."


class InvalidCoordinatesError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code = "INVALID_COORDINATES"
    message = "Latitude must be -90..90 and longitude must be -180..180."


class EmbeddingError(AppError):
    status_code = status.HTTP_502_BAD_GATEWAY
    error_code = "EMBEDDING_FAILED"
    message = "Failed to generate or store embedding vector."


class QdrantUnavailableError(AppError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    error_code = "QDRANT_UNAVAILABLE"
    message = "Vector database is temporarily unavailable."

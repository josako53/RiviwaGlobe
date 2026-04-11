"""core/exceptions.py — Domain exceptions for ai_service."""
from __future__ import annotations
from typing import Any, Optional
from fastapi import status


class AppError(Exception):
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code:  str = "INTERNAL_ERROR"
    message:     str = "An unexpected error occurred."

    def __init__(self, message: Optional[str] = None, detail: Optional[dict[str, Any]] = None,
                 *, error_code: Optional[str] = None, status_code: Optional[int] = None) -> None:
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


class ValidationError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code  = "VALIDATION_ERROR"
    message     = "The submitted data is invalid."

class UnauthorisedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code  = "UNAUTHORISED"
    message     = "Authentication is required."

class TokenExpiredError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code  = "TOKEN_EXPIRED"
    message     = "Your session has expired."

class TokenInvalidError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code  = "TOKEN_INVALID"
    message     = "The provided token is invalid."

class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    error_code  = "FORBIDDEN"
    message     = "You do not have permission to perform this action."

class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code  = "NOT_FOUND"
    message     = "Resource not found."

class ConversationNotFoundError(NotFoundError):
    error_code = "CONVERSATION_NOT_FOUND"
    message    = "AI conversation session not found."

class OllamaUnavailableError(AppError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    error_code  = "OLLAMA_UNAVAILABLE"
    message     = "AI model is temporarily unavailable. Please try again shortly."

class FeedbackSubmissionError(AppError):
    status_code = status.HTTP_502_BAD_GATEWAY
    error_code  = "FEEDBACK_SUBMISSION_FAILED"
    message     = "Failed to submit feedback. Please try again."

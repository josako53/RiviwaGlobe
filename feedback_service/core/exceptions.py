"""core/exceptions.py — Domain exceptions for feedback_service."""
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

class FeedbackNotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code  = "FEEDBACK_NOT_FOUND"
    message     = "Feedback record not found."

class ProjectNotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code  = "PROJECT_NOT_FOUND"
    message     = "Project not found or not yet synced from auth service."

class CommitteeNotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code  = "COMMITTEE_NOT_FOUND"
    message     = "Grievance Handling Committee not found."

class EscalationError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code  = "ESCALATION_ERROR"
    message     = "Cannot escalate: feedback is not in a valid state for escalation."

class ResolutionError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code  = "RESOLUTION_ERROR"
    message     = "Cannot resolve: feedback is not in a valid state for resolution."

class AppealError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code  = "APPEAL_ERROR"
    message     = "Cannot file appeal: feedback is either not resolved or an appeal already exists."

class FeedbackClosedError(AppError):
    status_code = status.HTTP_409_CONFLICT
    error_code  = "FEEDBACK_CLOSED"
    message     = "This feedback record is already closed and cannot be modified."

class ProjectNotAcceptingFeedbackError(AppError):
    status_code = status.HTTP_409_CONFLICT
    error_code  = "PROJECT_NOT_ACCEPTING_FEEDBACK"
    message     = "This project is not currently accepting this type of feedback."


class NotFoundError(AppError):
    status_code = 404
    def __init__(self, message: str = "Resource not found."):
        super().__init__(message)


class ChannelSessionNotFoundError(NotFoundError):
    def __init__(self):
        super().__init__("Channel session not found.")

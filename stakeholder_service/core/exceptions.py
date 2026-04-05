"""
core/exceptions.py
═══════════════════════════════════════════════════════════════════════════════
Domain exception hierarchy for the stakeholder_service.

Follows the exact same pattern as auth_service/core/exceptions.py:
  · machine-readable error_code  (SCREAMING_SNAKE_CASE)
  · human-readable message
  · HTTP status_code
  · optional detail dict

HTTP response shape:
    {
        "error":   "STAKEHOLDER_NOT_FOUND",
        "message": "Stakeholder not found.",
        "detail":  { … }    ← omitted when empty
    }
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import status


# ─────────────────────────────────────────────────────────────────────────────
# Base
# ─────────────────────────────────────────────────────────────────────────────

class AppError(Exception):
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code:  str = "INTERNAL_ERROR"
    message:     str = "An unexpected error occurred."

    def __init__(
        self,
        message:     Optional[str]            = None,
        detail:      Optional[dict[str, Any]] = None,
        *,
        error_code:  Optional[str]            = None,
        status_code: Optional[int]            = None,
    ) -> None:
        self.message     = message     or self.__class__.message
        self.detail:     dict[str, Any] = detail or {}
        self.error_code  = error_code  or self.__class__.error_code
        self.status_code = status_code or self.__class__.status_code
        super().__init__(self.message)

    def to_response_body(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "error":   self.error_code,
            "message": self.message,
        }
        if self.detail:
            body["detail"] = self.detail
        return body


# ─────────────────────────────────────────────────────────────────────────────
# 400 Bad Request
# ─────────────────────────────────────────────────────────────────────────────

class ValidationError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code  = "VALIDATION_ERROR"
    message     = "The submitted data is invalid."


class DuplicateContactError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code  = "DUPLICATE_CONTACT"
    message     = "This contact is already registered for this stakeholder."


class DuplicateStakeholderProjectError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code  = "DUPLICATE_STAKEHOLDER_PROJECT"
    message     = "This stakeholder is already registered under this project."


class InvalidDistributionError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code  = "INVALID_DISTRIBUTION"
    message     = "Distribution record is invalid or already exists."


# ─────────────────────────────────────────────────────────────────────────────
# 401 Unauthorised
# ─────────────────────────────────────────────────────────────────────────────

class UnauthorisedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code  = "UNAUTHORISED"
    message     = "Authentication is required."


class TokenExpiredError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code  = "TOKEN_EXPIRED"
    message     = "Your session has expired. Please log in again."


class TokenInvalidError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code  = "TOKEN_INVALID"
    message     = "The provided token is invalid."


# ─────────────────────────────────────────────────────────────────────────────
# 403 Forbidden
# ─────────────────────────────────────────────────────────────────────────────

class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    error_code  = "FORBIDDEN"
    message     = "You do not have permission to perform this action."


# ─────────────────────────────────────────────────────────────────────────────
# 404 Not Found
# ─────────────────────────────────────────────────────────────────────────────

class StakeholderNotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code  = "STAKEHOLDER_NOT_FOUND"
    message     = "Stakeholder not found."


class ContactNotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code  = "CONTACT_NOT_FOUND"
    message     = "Stakeholder contact not found."


class ProjectNotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code  = "PROJECT_NOT_FOUND"
    message     = "Project not found. It may not have been synced yet from the auth service."


class ActivityNotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code  = "ACTIVITY_NOT_FOUND"
    message     = "Engagement activity not found."


class CommunicationNotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code  = "COMMUNICATION_NOT_FOUND"
    message     = "Communication record not found."


class FocalPersonNotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code  = "FOCAL_PERSON_NOT_FOUND"
    message     = "Focal person not found."


# ─────────────────────────────────────────────────────────────────────────────
# 409 Conflict
# ─────────────────────────────────────────────────────────────────────────────

class ProjectAlreadySyncedError(AppError):
    status_code = status.HTTP_409_CONFLICT
    error_code  = "PROJECT_ALREADY_SYNCED"
    message     = "This project is already registered in the stakeholder service."


# ─────────────────────────────────────────────────────────────────────────────
# 422 Unprocessable
# ─────────────────────────────────────────────────────────────────────────────

class ContactRequiredError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code  = "CONTACT_REQUIRED"
    message     = (
        "At least one contact person is required for organizational or group stakeholders."
    )


class PrimaryContactRequiredError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code  = "PRIMARY_CONTACT_REQUIRED"
    message     = "At least one contact must be marked as primary."

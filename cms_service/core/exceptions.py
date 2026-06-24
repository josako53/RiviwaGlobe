from __future__ import annotations
from fastapi import status


class AppError(Exception):
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error:       str = "INTERNAL_ERROR"
    message:     str = "An unexpected error occurred."

    def __init__(self, message: str | None = None):
        if message:
            self.message = message
        super().__init__(self.message)

    def to_response_body(self) -> dict:
        return {"error": self.error, "message": self.message}


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    error       = "NOT_FOUND"
    message     = "Resource not found."


class UnauthorisedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    error       = "UNAUTHORISED"
    message     = "Authentication is required."


class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    error       = "FORBIDDEN"
    message     = "You do not have permission to perform this action."


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    error       = "CONFLICT"
    message     = "Resource already exists."


class ValidationError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error       = "VALIDATION_ERROR"
    message     = "Validation failed."

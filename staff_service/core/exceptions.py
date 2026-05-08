from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import HTTPException


class AppError(Exception):
    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"
    message: str = "An unexpected error occurred"

    def __init__(
        self,
        message: Optional[str] = None,
        detail: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.message = message or self.__class__.message
        self.detail = detail or {}
        super().__init__(self.message)

    def to_response_body(self) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "error_code": self.error_code,
            "message": self.message,
        }
        if self.detail:
            body["detail"] = self.detail
        return body

    def to_http_exception(self) -> HTTPException:
        return HTTPException(
            status_code=self.status_code,
            detail=self.to_response_body(),
        )


# ── Auth ──────────────────────────────────────────────────────────────────────

class TokenInvalidError(AppError):
    status_code = 401
    error_code = "TOKEN_INVALID"
    message = "Authentication token is invalid"


class TokenExpiredError(AppError):
    status_code = 401
    error_code = "TOKEN_EXPIRED"
    message = "Authentication token has expired"


class UnauthorisedError(AppError):
    status_code = 401
    error_code = "UNAUTHORISED"
    message = "Authentication required"


class ForbiddenError(AppError):
    status_code = 403
    error_code = "FORBIDDEN"
    message = "You do not have permission to perform this action"


# ── Staff ─────────────────────────────────────────────────────────────────────

class StaffNotFoundError(AppError):
    status_code = 404
    error_code = "STAFF_NOT_FOUND"
    message = "Staff profile not found"


class StaffCodeAlreadyExistsError(AppError):
    status_code = 409
    error_code = "STAFF_CODE_EXISTS"
    message = "A staff member with this code already exists for your organisation"


class StaffAlreadySuspendedError(AppError):
    status_code = 422
    error_code = "STAFF_ALREADY_SUSPENDED"
    message = "Staff member is already suspended"


class StaffAlreadyTerminatedError(AppError):
    status_code = 422
    error_code = "STAFF_ALREADY_TERMINATED"
    message = "Staff member is already terminated"


class StaffNotSuspendedError(AppError):
    status_code = 422
    error_code = "STAFF_NOT_SUSPENDED"
    message = "Staff member is not suspended"


# ── Fraud Report ──────────────────────────────────────────────────────────────

class FraudReportNotFoundError(AppError):
    status_code = 404
    error_code = "FRAUD_REPORT_NOT_FOUND"
    message = "Fraud report not found"


# ── Verification ──────────────────────────────────────────────────────────────

class VerificationEventNotFoundError(AppError):
    status_code = 404
    error_code = "VERIFICATION_EVENT_NOT_FOUND"
    message = "Verification event not found"


# ── Bulk Import ───────────────────────────────────────────────────────────────

class BulkImportJobNotFoundError(AppError):
    status_code = 404
    error_code = "BULK_IMPORT_JOB_NOT_FOUND"
    message = "Bulk import job not found"


# ── Storage ───────────────────────────────────────────────────────────────────

class InvalidFileTypeError(AppError):
    status_code = 422
    error_code = "INVALID_FILE_TYPE"
    message = "Only JPG, PNG, and WEBP images are accepted"


class FileTooLargeError(AppError):
    status_code = 422
    error_code = "FILE_TOO_LARGE"
    message = "File exceeds maximum allowed size of 5MB"


# ── Org ───────────────────────────────────────────────────────────────────────

class OrgNotFoundError(AppError):
    status_code = 404
    error_code = "ORG_NOT_FOUND"
    message = "Organisation not found"


class OrgInactiveError(AppError):
    status_code = 403
    error_code = "ORG_INACTIVE"
    message = "Organisation is not active"


class ValidationError(AppError):
    status_code = 422
    error_code = "VALIDATION_ERROR"
    message = "Validation failed"

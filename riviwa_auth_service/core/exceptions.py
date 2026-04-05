"""
core/exceptions.py
═══════════════════════════════════════════════════════════════════════════════
Domain exception hierarchy for the Riviwa auth service.

Design principles
─────────────────
  · Every exception carries a machine-readable error_code (SCREAMING_SNAKE_CASE)
    for frontend switch/case logic and monitoring dashboards.
  · Every exception carries a human-readable message for display to end users.
  · Every exception carries an HTTP status_code so FastAPI returns the
    correct HTTP status automatically via the global handler.
  · An optional detail dict carries structured extra context
    (e.g. verification_url, field names, retry_after_seconds).

HTTP response shape  (produced by register_exception_handlers)
──────────────────────────────────────────────────────────────
    {
        "error":   "INVALID_CREDENTIALS",
        "message": "Invalid identifier or password.",
        "detail":  { … }          ← omitted when empty
    }

Registration
────────────
    # main.py / application factory
    from app.core.exceptions import register_exception_handlers
    register_exception_handlers(app)
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

from typing import Any, Optional

import structlog
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

log = structlog.get_logger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Base
# ─────────────────────────────────────────────────────────────────────────────

class AppError(Exception):
    """
    Root for all application-level exceptions.

    Subclass convention (define as class-level attrs; override in __init__ when needed):

        class FooError(AppError):
            status_code = 409
            error_code  = "FOO_CONFLICT"
            message     = "Default human-readable message."
    """
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

class BadRequestError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code  = "BAD_REQUEST"
    message     = "The request is malformed or missing required parameters."


class WeakPasswordError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code  = "WEAK_PASSWORD"
    message     = (
        "Password must be at least 8 characters and include one uppercase letter, "
        "one lowercase letter, one digit, and one special character."
    )


class InvalidOTPError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code  = "INVALID_OTP"
    message     = "The verification code is incorrect."


class OTPExpiredError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code  = "OTP_EXPIRED"
    message     = "The verification code has expired. Please request a new one."


class OTPMaxAttemptsError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code  = "OTP_MAX_ATTEMPTS"
    message     = "Too many incorrect attempts. Please restart the verification flow."


class InvalidTokenError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code  = "INVALID_TOKEN"
    message     = "The provided token is invalid or has already been used."


class TokenExpiredError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code  = "TOKEN_EXPIRED"
    message     = "This link has expired. Please start over."


class PasswordMismatchError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code  = "PASSWORD_MISMATCH"
    message     = "The current password you entered is incorrect."


class SamePasswordError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code  = "SAME_PASSWORD"
    message     = "New password must be different from your current password."


class PasswordNotSetError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code  = "PASSWORD_NOT_SET"
    message     = "This account has no password. Please use social login or contact support."


class PasswordAlreadySetError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code  = "PASSWORD_ALREADY_SET"
    message     = "A password is already set on this account. Use the change-password flow."


class InvalidIdentifierError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code  = "INVALID_IDENTIFIER"
    message     = "Identifier must be a valid email address or E.164 phone number (e.g. +12125551234)."


# ─────────────────────────────────────────────────────────────────────────────
# 401 Unauthorised
# ─────────────────────────────────────────────────────────────────────────────

class UnauthorisedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code  = "UNAUTHORISED"
    message     = "Authentication credentials were not provided or are invalid."


class InvalidCredentialsError(AppError):
    """
    Intentionally vague — does not reveal whether the identifier exists.
    Used for wrong password / wrong identifier at login step 1.
    """
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code  = "INVALID_CREDENTIALS"
    message     = "Invalid identifier or password."


class AccessTokenExpiredError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code  = "ACCESS_TOKEN_EXPIRED"
    message     = "Your session has expired. Please refresh your token."


class AccessTokenRevokedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code  = "ACCESS_TOKEN_REVOKED"
    message     = "This session has been revoked. Please log in again."


class RefreshTokenInvalidError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code  = "REFRESH_TOKEN_INVALID"
    message     = "Refresh token is invalid or expired. Please log in again."


class OAuthTokenInvalidError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code  = "OAUTH_TOKEN_INVALID"
    message     = "Social login token verification failed. Please try again."


# ─────────────────────────────────────────────────────────────────────────────
# 403 Forbidden
# ─────────────────────────────────────────────────────────────────────────────

class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    error_code  = "FORBIDDEN"
    message     = "You do not have permission to perform this action."


class AccountSuspendedError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    error_code  = "ACCOUNT_SUSPENDED"
    message     = "Your account has been temporarily suspended. Please contact support."


class AccountBannedError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    error_code  = "ACCOUNT_BANNED"
    message     = "Your account has been permanently disabled."


class AccountDeactivatedError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    error_code  = "ACCOUNT_DEACTIVATED"
    message     = "This account has been deactivated."


class AccountLockedError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    error_code  = "ACCOUNT_LOCKED"
    message     = "Account is temporarily locked due to too many failed login attempts. Try again later."


class EmailNotVerifiedError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    error_code  = "EMAIL_NOT_VERIFIED"
    message     = "Please verify your email address before continuing."


class PhoneNotVerifiedError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    error_code  = "PHONE_NOT_VERIFIED"
    message     = "Please verify your phone number before continuing."


class IDVerificationRequiredError(AppError):
    """
    Raised by RegistrationService when fraud scoring triggers REVIEW.
    detail must contain:
        user_id                 str UUID
        verification_session_id str
        verification_url        str
    """
    status_code = status.HTTP_403_FORBIDDEN
    error_code  = "ID_VERIFICATION_REQUIRED"
    message     = "Identity verification is required to activate your account."


class FraudBlockedError(AppError):
    """Registration hard-blocked by the fraud scoring engine."""
    status_code = status.HTTP_403_FORBIDDEN
    error_code  = "FRAUD_BLOCKED"
    message     = "We were unable to create your account at this time."


class OrgNotActiveError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    error_code  = "ORG_NOT_ACTIVE"
    message     = "This organisation is not currently active."


class OrgMembershipRequiredError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    error_code  = "ORG_MEMBERSHIP_REQUIRED"
    message     = "You must be an active member of this organisation to perform this action."


class InsufficientOrgRoleError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    error_code  = "INSUFFICIENT_ORG_ROLE"
    message     = "Your role in this organisation does not permit this action."


class InsufficientPlatformRoleError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    error_code  = "INSUFFICIENT_PLATFORM_ROLE"
    message     = "You do not have the required platform staff role for this action."


# ─────────────────────────────────────────────────────────────────────────────
# 404 Not Found
# ─────────────────────────────────────────────────────────────────────────────

class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code  = "NOT_FOUND"
    message     = "The requested resource was not found."


class UserNotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code  = "USER_NOT_FOUND"
    message     = "User not found."


class OrgNotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code  = "ORG_NOT_FOUND"
    message     = "Organisation not found."


class OrgMemberNotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code  = "ORG_MEMBER_NOT_FOUND"
    message     = "Organisation member not found."


class InviteNotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code  = "INVITE_NOT_FOUND"
    message     = "Invitation not found or no longer valid."


# ─────────────────────────────────────────────────────────────────────────────
# 409 Conflict
# ─────────────────────────────────────────────────────────────────────────────

class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    error_code  = "CONFLICT"
    message     = "A conflict occurred with the current state of the resource."


class DuplicateIdentifierError(AppError):
    """
    Generic uniqueness violation raised by RegistrationService when the
    exact duplicate type is already known to the caller but a single
    exception class is more convenient than branching on three separate ones.

    Prefer the specific variants (EmailAlreadyExistsError etc.) when the
    error must carry a field-level hint to the client.
    """
    status_code = status.HTTP_409_CONFLICT
    error_code  = "DUPLICATE_IDENTIFIER"
    message     = "An account with this email, phone number, or username already exists."


class EmailAlreadyExistsError(AppError):
    status_code = status.HTTP_409_CONFLICT
    error_code  = "EMAIL_ALREADY_EXISTS"
    message     = "An account with this email address already exists."


class PhoneAlreadyExistsError(AppError):
    status_code = status.HTTP_409_CONFLICT
    error_code  = "PHONE_ALREADY_EXISTS"
    message     = "An account with this phone number already exists."


class UsernameAlreadyExistsError(AppError):
    status_code = status.HTTP_409_CONFLICT
    error_code  = "USERNAME_ALREADY_EXISTS"
    message     = "This username is already taken. Please choose another."


class OrgSlugAlreadyExistsError(AppError):
    status_code = status.HTTP_409_CONFLICT
    error_code  = "ORG_SLUG_ALREADY_EXISTS"
    message     = "An organisation with this URL handle already exists."


class OrgMemberAlreadyExistsError(AppError):
    status_code = status.HTTP_409_CONFLICT
    error_code  = "ORG_MEMBER_ALREADY_EXISTS"
    message     = "This user is already a member of the organisation."


class InviteAlreadyPendingError(AppError):
    status_code = status.HTTP_409_CONFLICT
    error_code  = "INVITE_ALREADY_PENDING"
    message     = "An active invitation for this address already exists."


class IDAlreadyUsedError(AppError):
    """Government ID hash already linked to an approved account — permanent duplicate guard."""
    status_code = status.HTTP_409_CONFLICT
    error_code  = "ID_ALREADY_USED"
    message     = "This government ID is already associated with another account."


# ─────────────────────────────────────────────────────────────────────────────
# 422 Validation
# ─────────────────────────────────────────────────────────────────────────────

class ValidationError(AppError):
    """Business-logic validation that Pydantic cannot catch at the schema layer."""
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code  = "VALIDATION_ERROR"
    message     = "The submitted data failed validation."


class IDVerificationFailedError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code  = "ID_VERIFICATION_FAILED"
    message     = "Identity verification failed. Please try again with a valid government ID."


# ─────────────────────────────────────────────────────────────────────────────
# 429 Rate Limit
# ─────────────────────────────────────────────────────────────────────────────

class RateLimitError(AppError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    error_code  = "RATE_LIMIT_EXCEEDED"
    message     = "Too many requests. Please wait before trying again."


class OTPResendLimitError(AppError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    error_code  = "OTP_RESEND_LIMIT"
    message     = "Resend limit reached. Please wait before requesting another code."


class OTPCooldownError(AppError):
    """
    Raised when a resend is requested before the per-session cooldown expires.

    Pass the remaining wait time via `detail`:
        raise OTPCooldownError(detail={"retry_after_seconds": 42})

    Distinct from OTPResendLimitError, which is a hard count cap.
    OTPCooldownError is a time-window guard (default 60 s between resends).
    """
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    error_code  = "OTP_COOLDOWN"
    message     = "Please wait before requesting another verification code."


# ─────────────────────────────────────────────────────────────────────────────
# 500 Internal Server Error
# ─────────────────────────────────────────────────────────────────────────────

class InternalError(AppError):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code  = "INTERNAL_ERROR"
    message     = "An unexpected error occurred. Please try again later."


class DatabaseError(AppError):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code  = "DATABASE_ERROR"
    message     = "A database error occurred. Please try again later."


class OTPDeliveryError(AppError):
    """
    Raised when the OTP provider (Twilio, SMTP, etc.) rejects or blocks
    the delivery attempt.

    Common causes:
      · Twilio trial account — destination number not verified in the console.
      · Carrier or geo-block on the destination number.
      · Twilio Verify service rate-limit or fraud block.
      · Invalid / inactive Verify Service SID.

    Pass provider details via `detail` for logging:
        raise OTPDeliveryError(detail={"provider": "twilio", "code": 403, "reason": "..."})
    """
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    error_code  = "OTP_DELIVERY_FAILED"
    message     = "We were unable to send the verification code. Please check your phone number and try again."


class KafkaPublishError(AppError):
    """
    Only raise when a Kafka publish failure MUST surface to the caller.
    Normally Kafka errors are logged and swallowed so requests never fail
    due to the event bus being down.
    """
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code  = "EVENT_PUBLISH_ERROR"
    message     = "Failed to publish domain event."


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI exception handler registration
# ─────────────────────────────────────────────────────────────────────────────

async def _app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    log.warning(
        "app_error",
        error_code=exc.error_code,
        http_status=exc.status_code,
        message=exc.message,
        path=request.url.path,
        method=request.method,
        detail=exc.detail or None,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_response_body(),
    )


async def _unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    log.exception(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        exc_type=type(exc).__name__,
        exc_info=exc,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error":   "INTERNAL_ERROR",
            "message": "An unexpected error occurred. Please try again later.",
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register domain + catch-all exception handlers on the FastAPI app.

    Call once in main.py before the app starts serving requests:

        from app.core.exceptions import register_exception_handlers
        register_exception_handlers(app)
    """
    app.add_exception_handler(AppError,  _app_error_handler)        # type: ignore[arg-type]
    app.add_exception_handler(Exception, _unhandled_error_handler)  # type: ignore[arg-type]
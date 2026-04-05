# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  notification_service  |  Port: 8060  |  DB: notification_db (5437)
# FILE     :  core/exceptions.py
# ───────────────────────────────────────────────────────────────────────────
"""core/exceptions.py — Domain exceptions for notification_service."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import status


# ─────────────────────────────────────────────────────────────────────────────
# Base
# ─────────────────────────────────────────────────────────────────────────────

class AppError(Exception):
    """
    Base class for all notification_service domain errors.
    Subclass and override status_code, error_code, and message.
    """
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


# ─────────────────────────────────────────────────────────────────────────────
# 400-series
# ─────────────────────────────────────────────────────────────────────────────

class ValidationError(AppError):
    """Invalid request data — field validation failed."""
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code  = "VALIDATION_ERROR"
    message     = "Request validation failed."


class NotFoundError(AppError):
    """Requested resource does not exist."""
    status_code = status.HTTP_404_NOT_FOUND
    error_code  = "NOT_FOUND"
    message     = "The requested resource was not found."


class ForbiddenError(AppError):
    """Authenticated but not authorised for this action."""
    status_code = status.HTTP_403_FORBIDDEN
    error_code  = "FORBIDDEN"
    message     = "You do not have permission to perform this action."


class UnauthorisedError(AppError):
    """Missing or invalid service key / JWT."""
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code  = "UNAUTHORISED"
    message     = "Authentication required."


# ─────────────────────────────────────────────────────────────────────────────
# Notification-specific
# ─────────────────────────────────────────────────────────────────────────────

class TemplateNotFoundError(AppError):
    """
    No active NotificationTemplate row exists for the requested
    (notification_type, channel, language) combination.
    DeliveryService skips the channel when this is raised.
    """
    status_code = status.HTTP_404_NOT_FOUND
    error_code  = "TEMPLATE_NOT_FOUND"
    message     = "No active template found for this notification type and channel."


class ChannelNotConfiguredError(AppError):
    """
    The requested channel has no provider credentials configured.
    E.g. FCM_PROJECT_ID is empty so push cannot be sent.
    """
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    error_code  = "CHANNEL_NOT_CONFIGURED"
    message     = "The notification channel is not configured on this server."


class DeliveryMaxRetriesError(AppError):
    """
    A notification delivery has exhausted its retry budget.
    The delivery record is marked FAILED and no further retries will be attempted.
    """
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code  = "DELIVERY_MAX_RETRIES"
    message     = "Notification delivery failed after maximum retry attempts."


class InvalidChannelError(AppError):
    """Unknown channel name supplied in a request."""
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code  = "INVALID_CHANNEL"
    message     = "Invalid notification channel. Must be: in_app, push, sms, whatsapp, or email."


class InvalidPriorityError(AppError):
    """Unknown priority string supplied in a request."""
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code  = "INVALID_PRIORITY"
    message     = "Invalid priority. Must be: critical, high, medium, or low."


class DeviceNotFoundError(AppError):
    """Push device token record not found for this user."""
    status_code = status.HTTP_404_NOT_FOUND
    error_code  = "DEVICE_NOT_FOUND"
    message     = "Push device not found or does not belong to this user."

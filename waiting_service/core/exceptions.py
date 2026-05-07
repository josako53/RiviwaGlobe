from __future__ import annotations

from typing import Any, Optional

import structlog
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

log = structlog.get_logger(__name__)


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
        body: dict[str, Any] = {"error": self.error_code, "message": self.message}
        if self.detail:
            body["detail"] = self.detail
        return body


class InvalidFlowStepError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code  = "INVALID_FLOW_STEP"
    message     = "The requested flow step is invalid or out of order."


class PriorityEscalationError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code  = "PRIORITY_ESCALATION_ERROR"
    message     = "Priority change is not permitted in the current ticket state."


class UnauthorisedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code  = "UNAUTHORISED"
    message     = "Authentication credentials were not provided or are invalid."


class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    error_code  = "FORBIDDEN"
    message     = "You do not have permission to perform this action."


class TicketNotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code  = "TICKET_NOT_FOUND"
    message     = "Queue ticket not found."


class ServicePointNotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code  = "SERVICE_POINT_NOT_FOUND"
    message     = "Service point not found."


class ServiceFlowNotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code  = "SERVICE_FLOW_NOT_FOUND"
    message     = "Service flow not found."


class StaffCounterNotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code  = "STAFF_COUNTER_NOT_FOUND"
    message     = "Staff counter not found."


class UrgencyRequestNotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code  = "URGENCY_REQUEST_NOT_FOUND"
    message     = "Urgency request not found."


class StaffSessionNotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code  = "STAFF_SESSION_NOT_FOUND"
    message     = "Staff session not found."


class OrgNotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code  = "ORG_NOT_FOUND"
    message     = "Organisation not found."


class TicketNotWaitingError(AppError):
    status_code = status.HTTP_409_CONFLICT
    error_code  = "TICKET_NOT_WAITING"
    message     = "The ticket is not in a WAITING state and cannot be called."


class NoTicketsWaitingError(AppError):
    status_code = status.HTTP_409_CONFLICT
    error_code  = "NO_TICKETS_WAITING"
    message     = "There are no tickets waiting at this service point."


class CounterAlreadyBusyError(AppError):
    status_code = status.HTTP_409_CONFLICT
    error_code  = "COUNTER_ALREADY_BUSY"
    message     = "This counter is already serving a ticket."


class SessionAlreadyOpenError(AppError):
    status_code = status.HTTP_409_CONFLICT
    error_code  = "SESSION_ALREADY_OPEN"
    message     = "This counter already has an active staff session."


class InternalError(AppError):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code  = "INTERNAL_ERROR"
    message     = "An unexpected error occurred. Please try again later."


async def _app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    log.warning(
        "app_error",
        error_code=exc.error_code,
        status_code=exc.status_code,
        message=exc.message,
        path=request.url.path,
    )
    return JSONResponse(status_code=exc.status_code, content=exc.to_response_body())


async def _unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    log.exception("unhandled_exception", path=request.url.path, exc_type=type(exc).__name__)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "INTERNAL_ERROR", "message": "An unexpected error occurred."},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error_handler)        # type: ignore[arg-type]
    app.add_exception_handler(Exception, _unhandled_error_handler) # type: ignore[arg-type]

"""core/exceptions.py — payment_service"""
from __future__ import annotations


class AppError(Exception):
    status_code: int = 500
    def __init__(self, message: str = "An error occurred."):
        super().__init__(message)
        self.message = message

class ValidationError(AppError):
    status_code = 422
class UnauthorisedError(AppError):
    status_code = 401
class ForbiddenError(AppError):
    status_code = 403
class NotFoundError(AppError):
    status_code = 404
    def __init__(self, message: str = "Resource not found."):
        super().__init__(message)
class ConflictError(AppError):
    status_code = 409
class PaymentProviderError(AppError):
    status_code = 502
    def __init__(self, provider: str, message: str):
        super().__init__(f"{provider}: {message}")
        self.provider = provider
class PaymentNotFoundError(NotFoundError):
    def __init__(self): super().__init__("Payment not found.")
class TransactionNotFoundError(NotFoundError):
    def __init__(self): super().__init__("Transaction not found.")
class DuplicatePaymentError(ConflictError):
    def __init__(self): super().__init__("A payment with this reference already exists.")

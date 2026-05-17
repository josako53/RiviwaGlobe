"""core/exceptions.py — Custom exceptions for subscription_service."""
from __future__ import annotations
from fastapi import HTTPException


class AppError(HTTPException):
    def __init__(self, status_code: int, error: str, message: str):
        super().__init__(status_code=status_code, detail={"error": error, "message": message})


class NotFoundError(AppError):
    def __init__(self, resource: str = "Resource"):
        super().__init__(404, "NOT_FOUND", f"{resource} not found.")


class ConflictError(AppError):
    def __init__(self, message: str):
        super().__init__(409, "CONFLICT", message)


class ValidationError(AppError):
    def __init__(self, message: str):
        super().__init__(400, "VALIDATION_ERROR", message)


class PaymentError(AppError):
    def __init__(self, message: str):
        super().__init__(402, "PAYMENT_ERROR", message)


class SubscriptionError(AppError):
    def __init__(self, message: str):
        super().__init__(400, "SUBSCRIPTION_ERROR", message)


class PromoError(AppError):
    def __init__(self, message: str):
        super().__init__(400, "PROMO_ERROR", message)


class FeatureNotAvailable(AppError):
    def __init__(self, feature: str):
        super().__init__(403, "FEATURE_NOT_AVAILABLE",
                         f"'{feature}' is not available on your current plan. Upgrade to unlock.")

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


# ── Product ───────────────────────────────────────────────────────────────────

class ProductNotFoundError(AppError):
    status_code = 404
    error_code = "PRODUCT_NOT_FOUND"
    message = "Product not found"


class ProductTypeImmutableError(AppError):
    status_code = 422
    error_code = "PRODUCT_TYPE_IMMUTABLE"
    message = "Product type cannot be changed after the listing is published"


class ProductAlreadyPublishedError(AppError):
    status_code = 422
    error_code = "PRODUCT_ALREADY_PUBLISHED"
    message = "Product is already published"


class ProductNotPublishableError(AppError):
    status_code = 422
    error_code = "PRODUCT_NOT_PUBLISHABLE"
    message = "Product cannot be published — required fields are missing"


class BulletPointLimitError(AppError):
    status_code = 422
    error_code = "BULLET_POINT_LIMIT"
    message = "A product can have at most 5 bullet points"


class DuplicateSkuError(AppError):
    status_code = 409
    error_code = "DUPLICATE_SKU"
    message = "A product with this SKU already exists for your organisation"


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


class ImageNotFoundError(AppError):
    status_code = 404
    error_code = "IMAGE_NOT_FOUND"
    message = "Image not found"

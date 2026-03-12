from __future__ import annotations

from fastapi import HTTPException, status

from app.core.exceptions import (
    AppError,
    ConfigurationError,
    ConflictError,
    ExternalServiceError,
    NotFoundError,
    ValidationError,
)


def map_app_error_to_http(error: AppError) -> HTTPException:
    if isinstance(error, ValidationError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": error.code, "message": error.message},
        )

    if isinstance(error, NotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": error.code, "message": error.message},
        )

    if isinstance(error, ConflictError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": error.code, "message": error.message},
        )

    if isinstance(error, ConfigurationError):
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": error.code, "message": error.message},
        )

    if isinstance(error, ExternalServiceError):
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": error.code, "message": error.message},
        )

    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail={"code": error.code, "message": error.message},
    )
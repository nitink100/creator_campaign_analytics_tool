from __future__ import annotations


class AppError(Exception):
    """Base application exception."""

    def __init__(self, message: str, code: str = "app_error") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


class ValidationError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message=message, code="validation_error")


class ConfigurationError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message=message, code="configuration_error")


class NotFoundError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message=message, code="not_found")


class ConflictError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message=message, code="conflict")


class RepositoryError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message=message, code="repository_error")


class ExternalServiceError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message=message, code="external_service_error")


class IngestionError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message=message, code="ingestion_error")


class RateLimitError(ExternalServiceError):
    def __init__(self, message: str = "External service rate limit reached") -> None:
        super().__init__(message=message)
        self.code = "rate_limit_error"
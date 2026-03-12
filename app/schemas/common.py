from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import DEFAULT_PAGE_SIZE


T = TypeVar("T")


class APIResponse(BaseModel):
    success: bool = True
    message: str | None = None


class ErrorResponse(BaseModel):
    success: bool = False
    code: str
    message: str


class PaginationMeta(BaseModel):
    limit: int = Field(default=DEFAULT_PAGE_SIZE, ge=1)
    offset: int = Field(default=0, ge=0)
    total: int = Field(default=0, ge=0)


class PaginatedResponse(APIResponse, Generic[T]):
    items: list[T]
    pagination: PaginationMeta


class TimestampedSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None
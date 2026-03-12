from __future__ import annotations

from fastapi import APIRouter

from app.core.exceptions import AppError
from app.core.logging import get_logger
from app.schemas.platform import PlatformFilterConfigResponse, PlatformsResponse
from app.services.platform_service import PlatformService
from app.utils.errors import map_app_error_to_http

router = APIRouter(prefix="/api/platforms", tags=["platforms"])
logger = get_logger(__name__)


@router.get("", response_model=PlatformsResponse)
async def list_platforms() -> PlatformsResponse:
    try:
        service = PlatformService()
        items = service.list_platforms()

        return PlatformsResponse(
            success=True,
            message="Platforms fetched successfully",
            items=items,
        )
    except AppError as exc:
        logger.exception("Failed to list platforms")
        raise map_app_error_to_http(exc)


@router.get("/filters", response_model=PlatformFilterConfigResponse)
async def get_platform_filter_config() -> PlatformFilterConfigResponse:
    try:
        service = PlatformService()
        data = service.get_filter_config()

        return PlatformFilterConfigResponse(
            success=True,
            message="Platform filter configuration fetched",
            data=data,
        )
    except AppError as exc:
        logger.exception("Failed to fetch platform filter config")
        raise map_app_error_to_http(exc)
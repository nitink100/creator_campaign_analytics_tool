from __future__ import annotations

from fastapi import APIRouter

from app.schemas.common import APIResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=APIResponse)
async def health_check() -> APIResponse:
    return APIResponse(success=True, message="OK")


@router.get("/ready", response_model=APIResponse)
async def readiness_check() -> APIResponse:
    return APIResponse(success=True, message="READY")
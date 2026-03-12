from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.logging import setup_logging, get_logger
from app.db.init_db import init_db
from app.routes.health import router as health_router
from app.routes.auth import router as auth_router
from app.routes.ingestion import router as ingestion_router
from app.routes.analytics import router as analytics_router
from app.routes.content import router as content_router
from app.routes.creators import router as creators_router
from app.routes.platform import router as platform_router
from app.routes.admin import router as admin_router
from app.routes.campaigns import router as campaigns_router
from app.deps.auth import get_current_user, get_current_admin_user

logger = get_logger(__name__)


async def cleanup_stale_runs():
    """Mark pending/running runs older than 30 minutes as FAILED on startup."""
    from app.db.session import AsyncSessionLocal
    from app.models.ingestion_run import IngestionRun
    from app.core.enums import IngestionStatusEnum
    from app.utils.datetime_utils import utc_now
    from sqlalchemy import update
    from sqlalchemy.exc import ProgrammingError
    from datetime import timedelta

    cutoff = utc_now() - timedelta(minutes=30)
    try:
        async with AsyncSessionLocal() as session:
            stmt = (
                update(IngestionRun)
                .where(
                    IngestionRun.status.in_([IngestionStatusEnum.PENDING.value, IngestionStatusEnum.RUNNING.value]),
                    IngestionRun.started_at < cutoff
                )
                .values(
                    status=IngestionStatusEnum.FAILED.value,
                    finished_at=utc_now(),
                    error_summary="Stale run cleaned up on startup (Ghost Run)"
                )
            )
            await session.execute(stmt)
            await session.commit()
            print("--- Stale Ingestion Runs Cleaned Up ---")
    except ProgrammingError as e:
        err_msg = str(e.orig) if hasattr(e, "orig") and e.orig else str(e)
        if "does not exist" in err_msg:
            logger.warning("Skipping stale run cleanup: table not found (e.g. fresh DB). %s", err_msg)
        else:
            raise

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("Starting application")
    await init_db()
    logger.info("Database initialized")
    await cleanup_stale_runs()
    yield
    logger.info("Shutting down application")


settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global exception handler ─────────────────────────────────────────────
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    from app.utils.errors import map_app_error_to_http

    http_exc = map_app_error_to_http(exc)
    return JSONResponse(
        status_code=http_exc.status_code,
        content=http_exc.detail,
    )


from pydantic import ValidationError as PydanticValidationError


@app.exception_handler(PydanticValidationError)
async def pydantic_validation_error_handler(
    request: Request, exc: PydanticValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"code": "validation_error", "message": str(exc)},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"code": "internal_error", "message": "An unexpected error occurred"},
    )


# ── Routes ────────────────────────────────────────────────────────────────
app.include_router(health_router)
app.include_router(auth_router)
# Protected API routes (require valid JWT)
app.include_router(ingestion_router, dependencies=[Depends(get_current_user)])
app.include_router(content_router, dependencies=[Depends(get_current_user)])
app.include_router(creators_router, dependencies=[Depends(get_current_user)])
app.include_router(platform_router, dependencies=[Depends(get_current_user)])
app.include_router(analytics_router, dependencies=[Depends(get_current_user)])
app.include_router(admin_router, dependencies=[Depends(get_current_admin_user)])
app.include_router(campaigns_router, dependencies=[Depends(get_current_user)])

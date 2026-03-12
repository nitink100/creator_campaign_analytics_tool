from __future__ import annotations

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import get_settings
from app.core.enums import IngestionTriggerEnum, PlatformEnum, SourceTypeEnum
from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.schemas.ingestion import IngestionRunRequest
from app.services.ingestion.sync_runner import run_ingestion

logger = get_logger(__name__)

_scheduler: AsyncIOScheduler | None = None


async def _cron_sync_job() -> None:
    """Execute a scheduled ingestion run."""
    logger.info("Cron sync job triggered")
    try:
        async with AsyncSessionLocal() as db:
            request = IngestionRunRequest(
                platform=PlatformEnum.YOUTUBE,
                source_type=SourceTypeEnum.API,
                trigger_type=IngestionTriggerEnum.CRON,
            )
            summary = await run_ingestion(db=db, request=request)
            logger.info(
                "Cron sync completed | status=%s creators_inserted=%d content_inserted=%d metrics_inserted=%d duration_ms=%s",
                summary.status,
                summary.creators_inserted,
                summary.content_inserted,
                summary.metrics_inserted,
                summary.duration_ms,
            )
    except Exception:
        logger.exception("Cron sync job failed")


def start_scheduler() -> None:
    """Start the APScheduler if cron sync is enabled."""
    global _scheduler
    settings = get_settings()

    if not settings.ENABLE_CRON_SYNC:
        logger.info("Cron sync is disabled, skipping scheduler startup")
        return

    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(
        _cron_sync_job,
        trigger=CronTrigger.from_crontab(settings.CRON_SCHEDULE),
        id="youtube_cron_sync",
        name="YouTube Cron Sync",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("Scheduler started | schedule=%s", settings.CRON_SCHEDULE)


def stop_scheduler() -> None:
    """Stop the APScheduler if it's running."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
        _scheduler = None

from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import IngestionStatusEnum
from app.models.ingestion_run import IngestionRun
from app.repos.base_repo import BaseRepo


class IngestionRunWriteRepo(BaseRepo):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)

    async def create_run(
        self,
        *,
        platform: str,
        source_type: str,
        trigger_type: str,
        started_at: datetime,
        config_snapshot: dict | None = None,
    ) -> IngestionRun:
        run = IngestionRun(
            platform=platform,
            source_type=source_type,
            trigger_type=trigger_type,
            status=IngestionStatusEnum.PENDING.value,
            started_at=started_at,
            config_snapshot=config_snapshot,
        )
        self.db.add(run)
        await self.flush()
        await self.refresh(run)
        return run

    async def mark_running(self, run: IngestionRun) -> IngestionRun:
        run.status = IngestionStatusEnum.RUNNING.value
        await self.flush()
        return run

    async def mark_success(
        self,
        run: IngestionRun,
        *,
        finished_at: datetime,
        duration_ms: int | None = None,
    ) -> IngestionRun:
        run.status = IngestionStatusEnum.SUCCESS.value
        run.finished_at = finished_at
        run.duration_ms = duration_ms
        await self.flush()
        return run

    async def mark_partial_success(
        self,
        run: IngestionRun,
        *,
        finished_at: datetime,
        error_summary: str | None = None,
        duration_ms: int | None = None,
    ) -> IngestionRun:
        run.status = IngestionStatusEnum.PARTIAL_SUCCESS.value
        run.finished_at = finished_at
        run.error_summary = error_summary
        run.duration_ms = duration_ms
        await self.flush()
        return run

    async def mark_failed(
        self,
        run: IngestionRun,
        *,
        finished_at: datetime,
        error_summary: str,
        duration_ms: int | None = None,
    ) -> IngestionRun:
        run.status = IngestionStatusEnum.FAILED.value
        run.finished_at = finished_at
        run.error_summary = error_summary
        run.duration_ms = duration_ms
        await self.flush()
        return run

    async def update_counts(
        self,
        run: IngestionRun,
        *,
        records_seen: int | None = None,
        creators_inserted: int | None = None,
        creators_updated: int | None = None,
        content_inserted: int | None = None,
        content_updated: int | None = None,
        metrics_inserted: int | None = None,
        metrics_updated: int | None = None,
        records_skipped: int | None = None,
        warnings_count: int | None = None,
        errors_count: int | None = None,
    ) -> IngestionRun:
        if records_seen is not None:
            run.records_seen = records_seen
        if creators_inserted is not None:
            run.creators_inserted = creators_inserted
        if creators_updated is not None:
            run.creators_updated = creators_updated
        if content_inserted is not None:
            run.content_inserted = content_inserted
        if content_updated is not None:
            run.content_updated = content_updated
        if metrics_inserted is not None:
            run.metrics_inserted = metrics_inserted
        if metrics_updated is not None:
            run.metrics_updated = metrics_updated
        if records_skipped is not None:
            run.records_skipped = records_skipped
        if warnings_count is not None:
            run.warnings_count = warnings_count
        if errors_count is not None:
            run.errors_count = errors_count
        await self.flush()
        return run
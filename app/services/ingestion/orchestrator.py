from __future__ import annotations



import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import IngestionError
from app.core.logging import get_logger
from app.repos.content.write import ContentWriteRepo
from app.repos.creator.write import CreatorWriteRepo
from app.repos.ingestion_run.read import IngestionRunReadRepo
from app.repos.ingestion_run.write import IngestionRunWriteRepo
from app.repos.metric.write import MetricWriteRepo
from app.schemas.ingestion import IngestionRunRequest, IngestionRunSummary
from app.services.ingestion.registry import IngestionAdapterRegistry
from app.services.ingestion.validator import (
    validate_content_record,
    validate_creator_record,
    validate_metric_record,
)
from app.utils.datetime_utils import utc_now

logger = get_logger(__name__)


class IngestionOrchestrator:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.run_write_repo = IngestionRunWriteRepo(db)
        self.run_read_repo = IngestionRunReadRepo(db)
        self.creator_repo = CreatorWriteRepo(db)
        self.content_repo = ContentWriteRepo(db)
        self.metric_repo = MetricWriteRepo(db)
        self.registry = IngestionAdapterRegistry()

    async def cleanup_stale_runs(self, timeout_minutes: int = 30) -> int:
        """Mark stale runs as FAILED."""
        from sqlalchemy import update, or_
        from datetime import timedelta
        from app.models.ingestion_run import IngestionRun
        from app.core.enums import IngestionStatusEnum

        cutoff = utc_now() - timedelta(minutes=timeout_minutes)
        
        stmt = (
            update(IngestionRun)
            .where(
                or_(
                    IngestionRun.status == IngestionStatusEnum.RUNNING.value,
                    IngestionRun.status == IngestionStatusEnum.PENDING.value,
                )
            )
            .where(IngestionRun.started_at < cutoff)
            .values(
                status=IngestionStatusEnum.FAILED.value,
                finished_at=utc_now(),
                error_summary=f"Stale run timeout ({timeout_minutes}m)",
            )
        )
        
        result = await self.db.execute(stmt)
        return result.rowcount

    async def run(self, request: IngestionRunRequest, run_id: str | None = None) -> IngestionRunSummary:
        started_at = utc_now()
        
        # Cleanup any ghost runs before starting
        try:
            cleaned_count = await self.cleanup_stale_runs()
            if cleaned_count > 0:
                logger.info("Cleaned up %d stale ingestion runs", cleaned_count)
                await self.db.commit()
        except Exception as e:
            logger.error("Failed to cleanup stale runs: %s", e)
            await self.db.rollback()

        if run_id:
            run = await self.run_read_repo.get_by_id(run_id)
            if not run:
                raise ValueError(f"IngestionRun {run_id} not found")
        else:
            run = await self.run_write_repo.create_run(
                platform=request.platform.value,
                source_type=request.source_type.value,
                trigger_type=request.trigger_type.value,
                started_at=started_at,
                config_snapshot={
                    "platform": request.platform.value,
                    "source_type": request.source_type.value,
                    "trigger_type": request.trigger_type.value,
                },
            )

        try:
            await self.run_write_repo.mark_running(run)
            await self.db.commit()

            channel_ids = request.channel_ids
            if channel_ids is None:
                from app.repos.creator.read import CreatorReadRepo
                read_repo = CreatorReadRepo(self.db)
                channel_ids = await read_repo.get_tracked_channel_ids(
                    request.platform.value,
                    user_id=request.user_id,
                )

            adapter_cls = self.registry.get_adapter_class(
                platform=request.platform.value,
                source_type=request.source_type.value,
            )
            adapter = adapter_cls()
            logger.info("Phase 0: Fetching data from platform | platform=%s channels=%d", request.platform.value, len(channel_ids))
            payload = await adapter.ingest(channel_ids=channel_ids)
            logger.info("Data fetched | creators=%d content=%d metrics=%d", len(payload.creators), len(payload.content_items), len(payload.metric_snapshots))

            # 🛠 Phase 1: Bulk Upsert Creators
            logger.info("Phase 1: Upserting creators...")
            creators_data = []
            for creator_record in payload.creators:
                try:
                    creator_record = validate_creator_record(creator_record)
                    creators_data.append({
                        "id": str(uuid.uuid4()), # New UUIDs, but ON CONFLICT will handle existing
                        "platform": creator_record.platform,
                        "source_type": creator_record.source_type,
                        "platform_creator_id": creator_record.platform_creator_id,
                        "creator_name": creator_record.creator_name,
                        "creator_handle": creator_record.creator_handle,
                        "channel_url": creator_record.channel_url,
                        "creator_description": creator_record.creator_description,
                        "country_code": creator_record.country_code,
                        "created_at_platform": creator_record.created_at_platform,
                        "subscriber_count": creator_record.subscriber_count,
                        "channel_view_count": creator_record.channel_view_count,
                        "video_count": creator_record.video_count,
                        "uploads_playlist_id": creator_record.uploads_playlist_id,
                        "thumbnail_url": creator_record.thumbnail_url,
                        "extra_metrics": creator_record.extra_metrics,
                        "raw_payload": creator_record.raw_payload,
                        "last_ingested_run_id": run.id,
                        "ingested_at": creator_record.ingested_at,
                    })
                except Exception:
                    continue

            await self.creator_repo.bulk_upsert_creators(creators_data)
            await self.db.flush()

            # Re-fetch creator map (platform_id -> internal_id) to link content
            from app.repos.creator.read import CreatorReadRepo
            creator_read_repo = CreatorReadRepo(self.db)
            all_creators = await creator_read_repo.get_all_by_platform(request.platform.value)
            creator_map = {c.platform_creator_id: c.id for c in all_creators}
            logger.info("Creators upserted | tracked_map_size=%d", len(creator_map))

            # 🛠 Phase 2: Bulk Upsert Content Items
            logger.info("Phase 2: Upserting content items...")
            content_data = []
            for content_record in payload.content_items:
                try:
                    content_record = validate_content_record(content_record)
                    creator_id = creator_map.get(content_record.platform_creator_id)
                    if not creator_id:
                        continue
                    content_data.append({
                        "id": str(uuid.uuid4()),
                        "platform": content_record.platform,
                        "creator_profile_id": creator_id,
                        "platform_content_id": content_record.platform_content_id,
                        "content_type": content_record.content_type,
                        "title": content_record.title,
                        "description": content_record.description,
                        "published_at": content_record.published_at,
                        "content_url": content_record.content_url,
                        "category_id": content_record.category_id,
                        "channel_title_snapshot": content_record.channel_title_snapshot,
                        "thumbnail_url": content_record.thumbnail_url,
                        "tags_json": content_record.tags_json,
                        "extra_metrics": content_record.extra_metrics,
                        "raw_payload": content_record.raw_payload,
                        "last_ingested_run_id": run.id,
                        "ingested_at": content_record.ingested_at,
                    })
                except Exception:
                    continue

            await self.content_repo.bulk_upsert_content_items(content_data)
            await self.db.flush()

            # Re-fetch content map (platform_id -> internal_id) to link metrics
            from app.repos.content.read import ContentReadRepo
            content_read_repo = ContentReadRepo(self.db)
            all_content = await content_read_repo.get_all_by_platform(request.platform.value)
            content_map = {c.platform_content_id: c.id for c in all_content}
            logger.info("Content items upserted | tracked_map_size=%d", len(content_map))

            # 🛠 Phase 3: Bulk Upsert Metric Snapshots
            logger.info("Phase 3: Upserting metric snapshots...")
            metrics_data = []
            for metric_record in payload.metric_snapshots:
                try:
                    metric_record = validate_metric_record(metric_record)
                    content_id = content_map.get(metric_record.platform_content_id)
                    if not content_id:
                        continue
                    metrics_data.append({
                        "content_item_id": content_id,
                        "captured_at": metric_record.captured_at,
                        "views": metric_record.views,
                        "likes": metric_record.likes,
                        "comments": metric_record.comments,
                        "engagement_rate": metric_record.engagement_rate,
                        "extra_metrics": metric_record.extra_metrics,
                        "raw_payload": metric_record.raw_payload,
                        "ingestion_run_id": run.id,
                    })
                except Exception:
                    continue

            await self.metric_repo.bulk_upsert_metric_snapshots(metrics_data)

            # Update final counts and mark success
            await self.run_write_repo.update_counts(
                run,
                records_seen=payload.records_seen,
                creators_inserted=len(creators_data), # Approximation since we don't know insert vs update easily in SQLite bulk
                creators_updated=0,
                content_inserted=len(content_data),
                content_updated=0,
                metrics_inserted=len(metrics_data),
                metrics_updated=0,
                records_skipped=payload.records_seen - len(metrics_data), 
                warnings_count=len(payload.warnings),
                errors_count=0,
            )

            finished_at = utc_now()
            duration_ms = int((finished_at - started_at).total_seconds() * 1000)
            await self.run_write_repo.mark_success(run, finished_at=finished_at, duration_ms=duration_ms)
            logger.info("Ingestion run completed successfully | run_id=%s duration=%dms", run.id, duration_ms)
            await self.db.commit()

            refreshed_run = await self.run_read_repo.get_by_id(run.id)
            return IngestionRunSummary.model_validate(refreshed_run)

        except Exception as exc:
            await self.db.rollback()
            finished_at = utc_now()
            duration_ms = int((finished_at - started_at).total_seconds() * 1000)

            try:
                await self.run_write_repo.mark_failed(
                    run,
                    finished_at=finished_at,
                    error_summary=str(exc),
                    duration_ms=duration_ms,
                )
                await self.db.commit()
            except Exception:
                await self.db.rollback()

            raise IngestionError(f"Ingestion run failed: {exc}") from exc
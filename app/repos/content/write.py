from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content_item import ContentItem
from app.repos.base_repo import BaseRepo
from app.repos.content.read import ContentReadRepo


class ContentWriteRepo(BaseRepo):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)
        self.read_repo = ContentReadRepo(db)

    async def upsert_content_item(
        self,
        *,
        platform: str,
        creator_profile_id: str,
        platform_content_id: str,
        content_type: str,
        title: str,
        description: str | None = None,
        published_at: datetime | None = None,
        content_url: str | None = None,
        category_id: str | None = None,
        channel_title_snapshot: str | None = None,
        thumbnail_url: str | None = None,
        tags_json: list | None = None,
        extra_metrics: dict | None = None,
        raw_payload: dict | None = None,
        last_ingested_run_id: str | None = None,
        ingested_at: datetime | None = None,
    ) -> tuple[ContentItem, bool]:
        existing = await self.read_repo.get_by_platform_content_id(
            platform=platform,
            platform_content_id=platform_content_id,
            include_deleted=True,
        )

        if existing:
            existing.deleted_at = None
            existing.creator_profile_id = creator_profile_id
            existing.content_type = content_type
            existing.title = title
            existing.description = description
            existing.published_at = published_at
            existing.content_url = content_url
            existing.category_id = category_id
            existing.channel_title_snapshot = channel_title_snapshot
            existing.thumbnail_url = thumbnail_url
            existing.tags_json = tags_json
            existing.extra_metrics = extra_metrics
            existing.raw_payload = raw_payload
            existing.last_ingested_run_id = last_ingested_run_id
            existing.ingested_at = ingested_at
            await self.flush()
            return existing, False

        item = ContentItem(
            platform=platform,
            creator_profile_id=creator_profile_id,
            platform_content_id=platform_content_id,
            content_type=content_type,
            title=title,
            description=description,
            published_at=published_at,
            content_url=content_url,
            category_id=category_id,
            channel_title_snapshot=channel_title_snapshot,
            thumbnail_url=thumbnail_url,
            tags_json=tags_json,
            extra_metrics=extra_metrics,
            raw_payload=raw_payload,
            last_ingested_run_id=last_ingested_run_id,
            ingested_at=ingested_at,
        )
        self.db.add(item)
        await self.flush()
        return item, True

    async def bulk_upsert_content_items(
        self,
        items_data: list[dict],
    ) -> int:
        """
        Efficiently upsert multiple content items using SQLite ON CONFLICT.
        """
        if not items_data:
            return 0

        from sqlalchemy.dialects.sqlite import insert

        stmt = insert(ContentItem).values(items_data)
        stmt = stmt.on_conflict_do_update(
            index_elements=["platform", "platform_content_id"],
            set_={
                "creator_profile_id": stmt.excluded.creator_profile_id,
                "content_type": stmt.excluded.content_type,
                "title": stmt.excluded.title,
                "description": stmt.excluded.description,
                "published_at": stmt.excluded.published_at,
                "content_url": stmt.excluded.content_url,
                "category_id": stmt.excluded.category_id,
                "channel_title_snapshot": stmt.excluded.channel_title_snapshot,
                "thumbnail_url": stmt.excluded.thumbnail_url,
                "tags_json": stmt.excluded.tags_json,
                "extra_metrics": stmt.excluded.extra_metrics,
                "raw_payload": stmt.excluded.raw_payload,
                "last_ingested_run_id": stmt.excluded.last_ingested_run_id,
                "ingested_at": stmt.excluded.ingested_at,
                "updated_at": datetime.now(),
                "deleted_at": None,
            },
        )
        result = await self.db.execute(stmt)
        return result.rowcount
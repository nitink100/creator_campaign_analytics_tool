from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.creator_profile import CreatorProfile
from app.models.user_tracked_creator import UserTrackedCreator
from app.repos.base_repo import BaseRepo
from app.repos.creator.read import CreatorReadRepo


class CreatorWriteRepo(BaseRepo):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)
        self.read_repo = CreatorReadRepo(db)

    async def upsert_creator(
        self,
        *,
        platform: str,
        source_type: str,
        platform_creator_id: str,
        creator_name: str,
        creator_handle: str | None = None,
        channel_url: str | None = None,
        creator_description: str | None = None,
        country_code: str | None = None,
        is_tracked: bool = True,
        created_at_platform: datetime | None = None,
        subscriber_count: int | None = None,
        channel_view_count: int | None = None,
        video_count: int | None = None,
        uploads_playlist_id: str | None = None,
        thumbnail_url: str | None = None,
        extra_metrics: dict | None = None,
        raw_payload: dict | None = None,
        last_ingested_run_id: str | None = None,
        ingested_at: datetime | None = None,
    ) -> tuple[CreatorProfile, bool]:
        existing = await self.read_repo.get_by_platform_creator_id(
            platform=platform,
            platform_creator_id=platform_creator_id,
            include_deleted=True,
        )

        if existing:
            existing.deleted_at = None
            existing.source_type = source_type
            existing.creator_name = creator_name
            existing.creator_handle = creator_handle
            existing.channel_url = channel_url
            existing.creator_description = creator_description
            existing.country_code = country_code
            existing.is_tracked = is_tracked
            existing.created_at_platform = created_at_platform
            existing.subscriber_count = subscriber_count
            existing.channel_view_count = channel_view_count
            existing.video_count = video_count
            existing.uploads_playlist_id = uploads_playlist_id
            existing.thumbnail_url = thumbnail_url
            existing.extra_metrics = extra_metrics
            existing.raw_payload = raw_payload
            existing.last_ingested_run_id = last_ingested_run_id
            existing.ingested_at = ingested_at
            await self.flush()
            return existing, False

        creator = CreatorProfile(
            platform=platform,
            source_type=source_type,
            platform_creator_id=platform_creator_id,
            creator_name=creator_name,
            creator_handle=creator_handle,
            channel_url=channel_url,
            creator_description=creator_description,
            country_code=country_code,
            is_tracked=is_tracked,
            created_at_platform=created_at_platform,
            subscriber_count=subscriber_count,
            channel_view_count=channel_view_count,
            video_count=video_count,
            uploads_playlist_id=uploads_playlist_id,
            thumbnail_url=thumbnail_url,
            extra_metrics=extra_metrics,
            raw_payload=raw_payload,
            last_ingested_run_id=last_ingested_run_id,
            ingested_at=ingested_at,
        )
        self.db.add(creator)
        await self.flush()
        return creator, True

    async def add_user_tracked_creator(self, user_id: str, creator_profile_id: str) -> None:
        """Link a user to a creator they track. Idempotent."""
        result = await self.db.execute(
            select(UserTrackedCreator).where(
                UserTrackedCreator.user_id == user_id,
                UserTrackedCreator.creator_profile_id == creator_profile_id,
            )
        )
        if result.scalar_one_or_none() is not None:
            return
        self.db.add(UserTrackedCreator(user_id=user_id, creator_profile_id=creator_profile_id))
        await self.flush()

    async def remove_user_tracked_creator(self, user_id: str, creator_profile_id: str) -> int:
        """Remove a user's tracking of a creator. Returns number removed (0 or 1)."""
        stmt = delete(UserTrackedCreator).where(
            UserTrackedCreator.user_id == user_id,
            UserTrackedCreator.creator_profile_id == creator_profile_id,
        )
        result = await self.db.execute(stmt)
        return result.rowcount

    async def bulk_upsert_creators(
        self,
        creators_data: list[dict],
    ) -> int:
        """
        Efficiently upsert multiple creators using ON CONFLICT (SQLite or Postgres).
        Returns the number of affected rows.
        """
        if not creators_data:
            return 0

        dialect_name = self.db.get_bind().dialect.name
        if dialect_name == "postgresql":
            from sqlalchemy.dialects.postgresql import insert
        else:
            from sqlalchemy.dialects.sqlite import insert

        stmt = insert(CreatorProfile).values(creators_data)
        stmt = stmt.on_conflict_do_update(
            index_elements=["platform", "platform_creator_id"],
            set_={
                "source_type": stmt.excluded.source_type,
                "creator_name": stmt.excluded.creator_name,
                "creator_handle": stmt.excluded.creator_handle,
                "channel_url": stmt.excluded.channel_url,
                "creator_description": stmt.excluded.creator_description,
                "country_code": stmt.excluded.country_code,
                "is_tracked": stmt.excluded.is_tracked,
                "created_at_platform": stmt.excluded.created_at_platform,
                "subscriber_count": stmt.excluded.subscriber_count,
                "channel_view_count": stmt.excluded.channel_view_count,
                "video_count": stmt.excluded.video_count,
                "uploads_playlist_id": stmt.excluded.uploads_playlist_id,
                "thumbnail_url": stmt.excluded.thumbnail_url,
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
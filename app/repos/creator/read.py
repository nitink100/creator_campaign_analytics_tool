from __future__ import annotations

from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.enums import SortDirectionEnum
from app.core.exceptions import NotFoundError
from app.models.content_item import ContentItem
from app.models.content_metric import ContentMetric
from app.models.creator_profile import CreatorProfile
from app.models.user_tracked_creator import UserTrackedCreator
from app.repos.base_repo import BaseRepo
from app.schemas.creator import CreatorListQuery


class CreatorReadRepo(BaseRepo):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)

    async def get_by_id(
        self, creator_id: str, user_id: str | None = None,
    ) -> CreatorProfile:
        stmt = select(CreatorProfile).where(
            CreatorProfile.id == creator_id,
            CreatorProfile.deleted_at.is_(None),
        )
        if user_id is not None:
            stmt = stmt.join(
                UserTrackedCreator,
                (UserTrackedCreator.creator_profile_id == CreatorProfile.id)
                & (UserTrackedCreator.user_id == user_id),
            )
        result = await self.db.execute(stmt)
        creator = result.scalar_one_or_none()
        if not creator:
            raise NotFoundError(f"Creator not found: {creator_id}")
        return creator

    async def get_by_platform_creator_id(
        self,
        *,
        platform: str,
        platform_creator_id: str,
        include_deleted: bool = True,
    ) -> CreatorProfile | None:
        stmt = select(CreatorProfile).where(
            CreatorProfile.platform == platform,
            CreatorProfile.platform_creator_id == platform_creator_id,
        )
        if not include_deleted:
            stmt = stmt.where(CreatorProfile.deleted_at.is_(None))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_by_platform(self, platform: str) -> list[CreatorProfile]:
        stmt = select(CreatorProfile).where(
            CreatorProfile.platform == platform,
            CreatorProfile.deleted_at.is_(None)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_tracked_channel_ids(self, platform: str, user_id: str | None = None) -> list[str]:
        if user_id:
            stmt = (
                select(CreatorProfile.platform_creator_id)
                .select_from(UserTrackedCreator)
                .join(CreatorProfile, CreatorProfile.id == UserTrackedCreator.creator_profile_id)
                .where(
                    UserTrackedCreator.user_id == user_id,
                    CreatorProfile.platform == platform,
                    CreatorProfile.deleted_at.is_(None),
                )
            )
        else:
            stmt = select(CreatorProfile.platform_creator_id).where(
                CreatorProfile.platform == platform,
                CreatorProfile.is_tracked.is_(True),
                CreatorProfile.deleted_at.is_(None),
            )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_tracked_creator_profile_ids(self, user_id: str) -> list[str]:
        """Return creator_profile_ids that this user tracks (for scoping analytics)."""
        stmt = select(UserTrackedCreator.creator_profile_id).where(
            UserTrackedCreator.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_creators(self, query: CreatorListQuery) -> tuple[list[dict], int]:
        latest_metrics_subquery = (
            select(
                ContentMetric.content_item_id.label("content_item_id"),
                func.max(ContentMetric.captured_at).label("max_captured_at"),
            )
            .where(ContentMetric.deleted_at.is_(None))
            .group_by(ContentMetric.content_item_id)
            .subquery()
        )
        latest_metric = aliased(ContentMetric)

        stmt = (
            select(
                CreatorProfile.id.label("creator_id"),
                CreatorProfile.platform_creator_id,
                CreatorProfile.creator_name,
                CreatorProfile.creator_handle,
                CreatorProfile.channel_url,
                CreatorProfile.thumbnail_url,
                CreatorProfile.subscriber_count,
                CreatorProfile.channel_view_count,
                CreatorProfile.video_count,
                func.avg(latest_metric.engagement_rate).label("latest_avg_engagement_rate"),
                func.sum(latest_metric.views).label("latest_total_views"),
                func.count(func.distinct(ContentItem.id)).label("total_content_items"),
            )
            .select_from(CreatorProfile)
        )
        if query.user_id:
            stmt = stmt.join(
                UserTrackedCreator,
                (UserTrackedCreator.creator_profile_id == CreatorProfile.id)
                & (UserTrackedCreator.user_id == query.user_id),
            )
        stmt = (
            stmt.outerjoin(ContentItem, ContentItem.creator_profile_id == CreatorProfile.id)
            .outerjoin(
                latest_metrics_subquery,
                latest_metrics_subquery.c.content_item_id == ContentItem.id,
            )
            .outerjoin(
                latest_metric,
                (latest_metric.content_item_id == ContentItem.id)
                & (latest_metric.captured_at == latest_metrics_subquery.c.max_captured_at),
            )
            .where(CreatorProfile.deleted_at.is_(None))
            .group_by(
                CreatorProfile.id,
                CreatorProfile.platform_creator_id,
                CreatorProfile.creator_name,
                CreatorProfile.creator_handle,
                CreatorProfile.channel_url,
                CreatorProfile.thumbnail_url,
                CreatorProfile.subscriber_count,
                CreatorProfile.channel_view_count,
                CreatorProfile.video_count,
            )
        )
        if query.creator_name:
            like_value = f"%{query.creator_name.strip()}%"
            stmt = stmt.where(CreatorProfile.creator_name.ilike(like_value))
        if query.platform is not None:
            stmt = stmt.where(CreatorProfile.platform == query.platform)
        if query.min_subscriber_count is not None:
            stmt = stmt.where(CreatorProfile.subscriber_count >= query.min_subscriber_count)
        if query.max_subscriber_count is not None:
            stmt = stmt.where(CreatorProfile.subscriber_count <= query.max_subscriber_count)
        if query.min_channel_view_count is not None:
            stmt = stmt.where(CreatorProfile.channel_view_count >= query.min_channel_view_count)
        if query.max_channel_view_count is not None:
            stmt = stmt.where(CreatorProfile.channel_view_count <= query.max_channel_view_count)
        if query.min_video_count is not None:
            stmt = stmt.where(CreatorProfile.video_count >= query.min_video_count)
        if query.max_video_count is not None:
            stmt = stmt.where(CreatorProfile.video_count <= query.max_video_count)

        count_stmt = select(func.count()).select_from(stmt.subquery())

        sort_column_map = {
            "creator_name": CreatorProfile.creator_name,
            "subscriber_count": CreatorProfile.subscriber_count,
            "channel_view_count": CreatorProfile.channel_view_count,
            "video_count": CreatorProfile.video_count,
            "created_at_platform": CreatorProfile.created_at_platform,
        }
        sort_column = sort_column_map[query.sort_by.value]
        order_by_clause = asc(sort_column) if query.sort_direction == SortDirectionEnum.ASC else desc(sort_column)

        stmt = stmt.order_by(order_by_clause).offset(query.offset).limit(query.limit)

        total_result = await self.db.execute(count_stmt)
        total = int(total_result.scalar_one() or 0)

        result = await self.db.execute(stmt)
        return [dict(row) for row in result.mappings().all()], total
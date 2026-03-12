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
from app.schemas.content import ContentListQuery


class ContentReadRepo(BaseRepo):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)

    async def get_by_id(
        self, content_id: str, user_id: str | None = None,
    ) -> ContentItem:
        stmt = select(ContentItem).where(
            ContentItem.id == content_id,
            ContentItem.deleted_at.is_(None),
        )
        if user_id is not None:
            stmt = stmt.where(
                ContentItem.creator_profile_id.in_(
                    select(UserTrackedCreator.creator_profile_id).where(
                        UserTrackedCreator.user_id == user_id,
                    ),
                ),
            )
        result = await self.db.execute(stmt)
        item = result.scalar_one_or_none()
        if not item:
            raise NotFoundError(f"Content item not found: {content_id}")
        return item

    async def get_by_platform_content_id(
        self,
        *,
        platform: str,
        platform_content_id: str,
        include_deleted: bool = True,
    ) -> ContentItem | None:
        stmt = select(ContentItem).where(
            ContentItem.platform == platform,
            ContentItem.platform_content_id == platform_content_id,
        )
        if not include_deleted:
            stmt = stmt.where(ContentItem.deleted_at.is_(None))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_by_platform(self, platform: str) -> list[ContentItem]:
        stmt = select(ContentItem).where(
            ContentItem.platform == platform,
            ContentItem.deleted_at.is_(None)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_content(self, query: ContentListQuery) -> tuple[list[dict], int]:
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
                ContentItem.id.label("content_id"),
                ContentItem.platform_content_id,
                CreatorProfile.id.label("creator_id"),
                CreatorProfile.creator_name,
                CreatorProfile.subscriber_count,
                ContentItem.title,
                ContentItem.published_at,
                ContentItem.content_url,
                ContentItem.category_id,
                ContentItem.thumbnail_url,
                latest_metric.views,
                latest_metric.likes,
                latest_metric.comments,
                latest_metric.engagement_rate,
            )
            .join(CreatorProfile, ContentItem.creator_profile_id == CreatorProfile.id)
            .outerjoin(
                latest_metrics_subquery,
                latest_metrics_subquery.c.content_item_id == ContentItem.id,
            )
            .outerjoin(
                latest_metric,
                (latest_metric.content_item_id == ContentItem.id)
                & (latest_metric.captured_at == latest_metrics_subquery.c.max_captured_at),
            )
            .where(
                ContentItem.deleted_at.is_(None),
                CreatorProfile.deleted_at.is_(None),
            )
        )
        if query.user_id is not None:
            stmt = stmt.where(
                ContentItem.creator_profile_id.in_(
                    select(UserTrackedCreator.creator_profile_id).where(
                        UserTrackedCreator.user_id == query.user_id,
                    ),
                ),
            )
        if query.creator_name:
            like_value = f"%{query.creator_name.strip()}%"
            stmt = stmt.where(CreatorProfile.creator_name.ilike(like_value))
        if query.published_after is not None:
            stmt = stmt.where(ContentItem.published_at >= query.published_after)
        if query.published_before is not None:
            stmt = stmt.where(ContentItem.published_at <= query.published_before)
        if query.min_subscriber_count is not None:
            stmt = stmt.where(CreatorProfile.subscriber_count >= query.min_subscriber_count)
        if query.max_subscriber_count is not None:
            stmt = stmt.where(CreatorProfile.subscriber_count <= query.max_subscriber_count)
        if query.min_views is not None:
            stmt = stmt.where(latest_metric.views >= query.min_views)
        if query.max_views is not None:
            stmt = stmt.where(latest_metric.views <= query.max_views)
        if query.min_likes is not None:
            stmt = stmt.where(latest_metric.likes >= query.min_likes)
        if query.max_likes is not None:
            stmt = stmt.where(latest_metric.likes <= query.max_likes)
        if query.min_comments is not None:
            stmt = stmt.where(latest_metric.comments >= query.min_comments)
        if query.max_comments is not None:
            stmt = stmt.where(latest_metric.comments <= query.max_comments)
        if query.min_engagement_rate is not None:
            stmt = stmt.where(latest_metric.engagement_rate >= query.min_engagement_rate)
        if query.max_engagement_rate is not None:
            stmt = stmt.where(latest_metric.engagement_rate <= query.max_engagement_rate)

        count_stmt = select(func.count()).select_from(stmt.subquery())

        sort_column_map = {
            "published_at": ContentItem.published_at,
            "views": latest_metric.views,
            "likes": latest_metric.likes,
            "comments": latest_metric.comments,
            "engagement_rate": latest_metric.engagement_rate,
            "subscriber_count": CreatorProfile.subscriber_count,
            "creator_name": CreatorProfile.creator_name,
        }
        sort_column = sort_column_map[query.sort_by.value]
        order_by_clause = asc(sort_column) if query.sort_direction == SortDirectionEnum.ASC else desc(sort_column)

        stmt = stmt.order_by(order_by_clause).offset(query.offset).limit(query.limit)

        total_result = await self.db.execute(count_stmt)
        total = int(total_result.scalar_one() or 0)

        result = await self.db.execute(stmt)
        return [dict(row) for row in result.mappings().all()], total
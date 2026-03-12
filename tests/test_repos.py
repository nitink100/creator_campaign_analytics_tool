import pytest
from datetime import datetime, timezone
from sqlalchemy import select

from app.repos.creator.write import CreatorWriteRepo
from app.repos.content.write import ContentWriteRepo
from app.repos.metric.write import MetricWriteRepo
from app.models.creator_profile import CreatorProfile
from app.models.content_item import ContentItem
from app.models.content_metric import ContentMetric
from app.core.enums import PlatformEnum, SourceTypeEnum

@pytest.mark.asyncio
async def test_creator_repo_upsert(db_session):
    repo = CreatorWriteRepo(db_session)
    now = datetime.now(timezone.utc)
    
    # 1. Insert new
    creator, created = await repo.upsert_creator(
        platform=PlatformEnum.YOUTUBE.value,
        source_type=SourceTypeEnum.API.value,
        platform_creator_id="test_creator_1",
        creator_name="Test Creator",
        creator_handle="@test",
        subscriber_count=1000,
        ingested_at=now
    )
    assert created is True
    assert creator.creator_name == "Test Creator"
    
    # 2. Update existing
    creator2, created2 = await repo.upsert_creator(
        platform=PlatformEnum.YOUTUBE.value,
        source_type=SourceTypeEnum.API.value,
        platform_creator_id="test_creator_1",
        creator_name="Test Creator Updated",
        creator_handle="@test",
        subscriber_count=2000,
        ingested_at=now
    )
    assert created2 is False
    assert creator2.id == creator.id
    assert creator2.creator_name == "Test Creator Updated"
    assert creator2.subscriber_count == 2000

@pytest.mark.asyncio
async def test_content_repo_upsert(db_session):
    creator_repo = CreatorWriteRepo(db_session)
    content_repo = ContentWriteRepo(db_session)
    now = datetime.now(timezone.utc)
    
    # Create creator
    creator, _ = await creator_repo.upsert_creator(
        platform=PlatformEnum.YOUTUBE.value,
        source_type=SourceTypeEnum.API.value,
        platform_creator_id="test_creator_2",
        creator_name="Test Creator 2",
    )
    
    # Insert new content
    content, created = await content_repo.upsert_content_item(
        platform=PlatformEnum.YOUTUBE.value,
        creator_profile_id=creator.id,
        platform_content_id="test_vid_1",
        content_type="video",
        title="First Video",
        ingested_at=now
    )
    
    assert created is True
    assert content.title == "First Video"
    
    # Update content
    content2, created2 = await content_repo.upsert_content_item(
        platform=PlatformEnum.YOUTUBE.value,
        creator_profile_id=creator.id,
        platform_content_id="test_vid_1",
        content_type="video",
        title="First Video Updated",
        ingested_at=now
    )
    
    assert created2 is False
    assert content2.title == "First Video Updated"
    assert content2.id == content.id
    
@pytest.mark.asyncio
async def test_metric_repo_upsert(db_session):
    creator_repo = CreatorWriteRepo(db_session)
    content_repo = ContentWriteRepo(db_session)
    metric_repo = MetricWriteRepo(db_session)
    
    creator, _ = await creator_repo.upsert_creator(
        platform=PlatformEnum.YOUTUBE.value,
        source_type=SourceTypeEnum.API.value,
        platform_creator_id="test_creator_3",
        creator_name="Test Creator 3",
    )
    content, _ = await content_repo.upsert_content_item(
        platform=PlatformEnum.YOUTUBE.value,
        creator_profile_id=creator.id,
        platform_content_id="test_vid_2",
        content_type="video",
        title="Second Video"
    )
    
    now = datetime.now(timezone.utc)
    
    # Insert new metric
    metric, created = await metric_repo.upsert_metric_snapshot(
        content_item_id=content.id,
        captured_at=now,
        views=1000,
        likes=50,
        comments=10
    )
    
    assert created is True
    assert metric.views == 1000
    
    # Update metric snapshot for same timestamp
    metric2, created2 = await metric_repo.upsert_metric_snapshot(
        content_item_id=content.id,
        captured_at=now,
        views=1050,
        likes=55,
        comments=12
    )
    
    assert created2 is False
    assert metric2.views == 1050
    assert metric2.id == metric.id

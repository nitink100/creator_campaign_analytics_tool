import pytest
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timezone

from app.deps.db import get_db_session
from app.main import app
from app.core.enums import PlatformEnum, SourceTypeEnum
from app.repos.creator.write import CreatorWriteRepo
from app.repos.content.write import ContentWriteRepo
from app.repos.metric.write import MetricWriteRepo

@pytest.mark.asyncio
async def test_analytics_endpoints(db_session):
    # Setup dummy data
    creator_repo = CreatorWriteRepo(db_session)
    content_repo = ContentWriteRepo(db_session)
    metric_repo = MetricWriteRepo(db_session)
    
    now = datetime.now(timezone.utc)
    
    creator, _ = await creator_repo.upsert_creator(
        platform=PlatformEnum.YOUTUBE.value,
        source_type=SourceTypeEnum.API.value,
        platform_creator_id="analytics_creator",
        creator_name="Analytics Creator",
        subscriber_count=50000
    )
    creator.is_tracked = True
    
    content, _ = await content_repo.upsert_content_item(
        platform=PlatformEnum.YOUTUBE.value,
        creator_profile_id=creator.id,
        platform_content_id="analytics_vid",
        content_type="video",
        title="Analytics Video",
        published_at=now
    )
    
    await metric_repo.upsert_metric_snapshot(
        content_item_id=content.id,
        captured_at=now,
        views=150000,
        likes=10000,
        comments=500
    )
    await db_session.commit()
    
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # Test summary endpoint
            response = await ac.get("/api/analytics/summary")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "data" in data
            assert data["data"]["total_creators"] >= 1
            assert data["data"]["total_views"] >= 150000
            
            # Test top creators endpoint
            response = await ac.get("/api/analytics/top-creators")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["items"]) >= 1
            assert data["items"][0]["creator_name"] == "Analytics Creator"
            
            # Test top content endpoint
            response = await ac.get("/api/analytics/top-content")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["items"]) >= 1
            assert data["items"][0]["title"] == "Analytics Video"
            assert data["items"][0]["views"] == 150000
    finally:
        app.dependency_overrides.clear()

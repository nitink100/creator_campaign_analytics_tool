from __future__ import annotations
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.db.base import Base
from app.deps.db import get_db_session
from app.main import app


@pytest_asyncio.fixture(scope="function")
async def client():
    # Use an in-memory database for testing
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db():
        async with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["message"] == "OK"


@pytest.mark.asyncio
async def test_ready(client):
    response = await client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["message"] == "READY"


@pytest.mark.asyncio
async def test_list_platforms(client):
    response = await client.get("/api/platforms")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "youtube" in data["items"]


@pytest.mark.asyncio
async def test_platform_filters(client):
    response = await client.get("/api/platforms/filters")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "youtube" in data["data"]
    youtube_config = data["data"]["youtube"]
    assert "content" in youtube_config["supported_filters"]
    assert "creator" in youtube_config["supported_filters"]


@pytest.mark.asyncio
async def test_list_creators_empty(client):
    response = await client.get("/api/creators")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["items"] == []
    assert data["pagination"]["total"] == 0


@pytest.mark.asyncio
async def test_list_content_empty(client):
    response = await client.get("/api/content")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["items"] == []


@pytest.mark.asyncio
async def test_analytics_summary_empty(client):
    response = await client.get("/api/analytics/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["total_creators"] == 0
    assert data["data"]["total_content_items"] == 0


@pytest.mark.asyncio
async def test_content_invalid_sort_field(client):
    """Invalid sort_by causes Pydantic ValidationError → 500 (caught by global handler)."""
    response = await client.get("/api/content?sort_by=INVALID")
    assert response.status_code == 422

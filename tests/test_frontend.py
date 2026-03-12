import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.base import Base
from app.deps.auth import get_current_admin_user
from app.models.user import User


async def _mock_admin_user():
    u = User(email="admin@test.com", hashed_password="", role="admin")
    u.id = "test-admin-id"
    return u


@pytest.mark.asyncio
async def test_admin_reset_db(db_engine):
    app.dependency_overrides[get_current_admin_user] = _mock_admin_user
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post("/api/admin/reset-db")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Database reset successfully" in data["message"]
    finally:
        app.dependency_overrides.pop(get_current_admin_user, None)


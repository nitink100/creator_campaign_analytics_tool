import pytest
import asyncio
from unittest.mock import patch, MagicMock
from app.services.ingestion.quota_tracker import QuotaTracker
from app.models.quota_usage import QuotaUsage
from sqlalchemy import select

@pytest.mark.asyncio
async def test_quota_tracker_records_usage(db_session):
    tracker = QuotaTracker()
    
    # Needs to reset singleton state for test isolation
    import app.services.ingestion.quota_tracker as qt
    qt._used = None
    qt._current_day = None

    class MockSessionManager:
        def __init__(self, session):
            self.session = session
        async def __aenter__(self):
            return self.session
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    # Patch AsyncSessionLocal to use our test db_session
    with patch('app.services.ingestion.quota_tracker.AsyncSessionLocal', return_value=MockSessionManager(db_session)):
        # Test recording usage
        await tracker.record(150)
        
        # Verify in memory
        usage = await tracker.get_usage()
        assert usage['used'] == 150
        assert usage['percent'] == 1.5
        assert usage['warning'] is False
        assert usage['critical'] is False
        
        # Verify in DB
        today = qt._today()
        stmt = select(QuotaUsage).where(QuotaUsage.date == today)
        result = await db_session.execute(stmt)
        row = result.scalar_one_or_none()
        
        assert row is not None
        assert row.units_used == 150


@pytest.mark.asyncio
async def test_quota_tracker_thresholds(db_session):
    tracker = QuotaTracker()
    import app.services.ingestion.quota_tracker as qt
    qt._used = None
    qt._current_day = None

    class MockSessionManager:
        def __init__(self, session):
            self.session = session
        async def __aenter__(self):
            return self.session
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    with patch('app.services.ingestion.quota_tracker.AsyncSessionLocal', return_value=MockSessionManager(db_session)):
        
        # Test nearing critical
        await tracker.record(9500)
        usage = await tracker.get_usage()
        
        assert usage['percent'] == 95.0
        assert usage['warning'] is True
        assert usage['critical'] is True
        
        # Because it's critical, we shouldn't be allowed to browse or search
        can_search = await tracker.can_search()
        can_browse = await tracker.can_browse()
        
        assert getattr(tracker, 'can_search') is not None
        assert getattr(tracker, 'can_browse') is not None
        assert can_search is False
        assert can_browse is False

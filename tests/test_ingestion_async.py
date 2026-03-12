import asyncio
import pytest
from datetime import datetime, timezone
from unittest.mock import patch

from app.schemas.ingestion import IngestionRunRequest
from app.services.ingestion.sync_runner import dispatch_ingestion
from app.core.enums import PlatformEnum, SourceTypeEnum, IngestionTriggerEnum
from app.models.ingestion_run import IngestionRun
from sqlalchemy import select


class MockBackgroundTasks:
    def __init__(self):
        self.tasks = []

    def add_task(self, func, *args, **kwargs):
        self.tasks.append((func, args, kwargs))


@pytest.mark.asyncio
async def test_dispatch_ingestion_creates_run_and_background_task(db_session):
    # Arrange: force Celery unavailable so we always use BackgroundTasks
    bg_tasks = MockBackgroundTasks()
    request = IngestionRunRequest(
        platform=PlatformEnum.YOUTUBE,
        source_type=SourceTypeEnum.API,
        trigger_type=IngestionTriggerEnum.MANUAL,
        channel_ids=["UC1234"],
    )

    # Act: patch Celery so connection fails and we fall back to BackgroundTasks
    with patch("app.core.celery_app.celery_app") as mock_celery:
        mock_celery.connection_or_acquire.side_effect = Exception("Redis unavailable")
        run_read = await dispatch_ingestion(
        db=db_session,
        request=request,
        background_tasks=bg_tasks,
        )

    # Assert 1: The function should reply back immediately with pending/running status
    assert run_read.status == "pending" or run_read.status == "running"
    run_id = run_read.id

    # Assert 2: The database should contain exactly 1 run with the same params
    stmt = select(IngestionRun).where(IngestionRun.id == run_id)
    result = await db_session.execute(stmt)
    db_run = result.scalar_one_or_none()
    
    assert db_run is not None
    assert db_run.platform == "youtube"
    
    # Assert 3: A background task must have been queued to carry out the heavy work
    assert len(bg_tasks.tasks) == 1
    func, args, kwargs = bg_tasks.tasks[0]
    
    from app.services.ingestion.sync_runner import _do_background_sync
    assert func == _do_background_sync
    assert args[0] == run_id
    assert args[1] == request


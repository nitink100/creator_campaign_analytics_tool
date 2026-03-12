import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.ingestion.orchestrator import IngestionOrchestrator
from app.schemas.ingestion import IngestionRunRequest
from app.core.enums import PlatformEnum, SourceTypeEnum, IngestionTriggerEnum
from app.services.ingestion.normalizer import NormalizedIngestionPayload
from app.models.ingestion_run import IngestionRun

@pytest.mark.asyncio
async def test_orchestrator_initializes_run_correctly(db_session):
    orchestrator = IngestionOrchestrator(db_session)

    # We mock the registry adapter completely to prevent actual API calls
    adapter_mock = MagicMock()
    # Provide a blank dummy payload to simulate a real response
    dummy_payload = NormalizedIngestionPayload(
        records_seen=0,
        creators=[],
        content_items=[],
        metric_snapshots=[],
        warnings=[]
    )
    
    # We must patch an async method properly
    async def async_ingest(*args, **kwargs):
        return dummy_payload
    adapter_mock.return_value.ingest = async_sessionmaker_mock = async_ingest

    with patch('app.services.ingestion.registry.IngestionAdapterRegistry.get_adapter_class', return_value=adapter_mock):
        request = IngestionRunRequest(
            platform=PlatformEnum.YOUTUBE,
            source_type=SourceTypeEnum.API,
            trigger_type=IngestionTriggerEnum.MANUAL,
            channel_ids=["UC123"]
        )

        summary = await orchestrator.run(request)
        
        assert summary is not None
        assert summary.platform == PlatformEnum.YOUTUBE.value
        assert summary.creators_inserted == 0
        assert summary.status == "success"

        # Check that it exists in DB
        stmt = select(IngestionRun)
        result = await db_session.execute(stmt)
        runs = result.scalars().all()
        assert len(runs) == 1
        assert runs[0].status == "success"
        assert runs[0].errors_count == 0

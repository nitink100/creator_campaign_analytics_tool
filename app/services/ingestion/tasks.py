from __future__ import annotations

import asyncio
from app.core.celery_app import celery_app
from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.schemas.ingestion import IngestionRunRequest
from app.services.ingestion.orchestrator import IngestionOrchestrator

logger = get_logger(__name__)

@celery_app.task(name="app.services.ingestion.tasks.run_ingestion_task")
def run_ingestion_task(run_id: str, request_data: dict) -> None:
    """
    Celery task to run ingestion.
    """
    # Since we're in a synchronous Celery worker, we use asyncio.run to execute the async orchestrator
    asyncio.run(_execute_ingestion(run_id, request_data))

async def _execute_ingestion(run_id: str, request_data: dict) -> None:
    try:
        request = IngestionRunRequest(**request_data)
        async with AsyncSessionLocal() as session:
            orchestrator = IngestionOrchestrator(session)
            # Orchestrator.run now handles stale run cleanup internally
            await orchestrator.run(request, run_id=run_id)
            logger.info(f"Successfully completed ingestion run {run_id}")
    except Exception as e:
        logger.exception(f"Ingestion task failed for run {run_id}: {e}")
        # Failsafe: Try to mark the run as failed if we have a session
        try:
            async with AsyncSessionLocal() as session:
                from app.repos.ingestion_run.read import IngestionRunReadRepo
                from app.repos.ingestion_run.write import IngestionRunWriteRepo
                from app.utils.datetime_utils import utc_now
                
                repo = IngestionRunReadRepo(session)
                run = await repo.get_by_id(run_id)
                if run and run.status in ("pending", "running"):
                    await IngestionRunWriteRepo(session).mark_failed(
                        run, 
                        finished_at=utc_now(), 
                        error_summary=f"Task Error: {str(e)[:200]}",
                        duration_ms=0
                    )
                    await session.commit()
        except Exception as inner_e:
            logger.error(f"Failsafe status update failed: {inner_e}")
        raise

from __future__ import annotations

import asyncio
from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.schemas.ingestion import IngestionRunRequest, IngestionRunRead
from app.services.ingestion.orchestrator import IngestionOrchestrator
from app.utils.datetime_utils import utc_now

logger = get_logger(__name__)


async def _do_background_sync(run_id: str, request: IngestionRunRequest) -> None:
    try:
        async with AsyncSessionLocal() as session:
            orchestrator = IngestionOrchestrator(session)
            await orchestrator.run(request, run_id=run_id)
    except Exception as e:
        logger.exception("Background ingestion failed unexpectedly | run_id=%s", run_id)
        
        # Failsafe: update run status to FAILED
        try:
            async with AsyncSessionLocal() as session:
                from app.repos.ingestion_run.read import IngestionRunReadRepo
                from app.repos.ingestion_run.write import IngestionRunWriteRepo
                from app.utils.datetime_utils import utc_now
                
                run = await IngestionRunReadRepo(session).get_by_id(run_id)
                if run and run.status in ("pending", "running"):
                    await IngestionRunWriteRepo(session).mark_failed(
                        run,
                        finished_at=utc_now(),
                        error_summary=str(e)[:255],
                        duration_ms=0,
                    )
                    await session.commit()
        except Exception as inner_e:
            logger.error("Failed to apply failsafe FAILED status to DB: %s", inner_e)


async def dispatch_ingestion(
    *,
    db: AsyncSession,
    request: IngestionRunRequest,
    background_tasks: BackgroundTasks,
) -> IngestionRunRead:
    from app.utils.datetime_utils import utc_now
    
    orchestrator = IngestionOrchestrator(db)
    run = await orchestrator.run_write_repo.create_run(
        platform=request.platform.value,
        source_type=request.source_type.value,
        trigger_type=request.trigger_type.value,
        started_at=utc_now(),
        config_snapshot={
            "platform": request.platform.value,
            "source_type": request.source_type.value,
            "trigger_type": request.trigger_type.value,
        },
    )
    await db.commit()
    await db.refresh(run)
    run_id = run.id

    # Dispatch to Celery if configured and healthy
    dispatched = False
    try:
        from app.core.celery_app import celery_app
        # Brief check if broker is reachable
        with celery_app.connection_or_acquire() as conn:
            conn.ensure_connection(max_retries=1, interval_start=0, interval_step=0.1)
        
        from app.services.ingestion.tasks import run_ingestion_task
        run_ingestion_task.delay(run_id, request.model_dump())
        logger.info(f"Dispatched ingestion run {run_id} to Celery")
        dispatched = True
    except Exception as e:
        logger.warning(f"Celery/Redis unavailable, falling back to BackgroundTasks: {e}")
        background_tasks.add_task(_do_background_sync, run_id, request)
        dispatched = True # Handled by fallback

    return IngestionRunRead.model_validate(run)
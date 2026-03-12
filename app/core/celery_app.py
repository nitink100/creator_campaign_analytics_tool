from __future__ import annotations

from celery import Celery
from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "creator_analytics",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    broker_connection_retry_on_startup=True,
)

celery_app.autodiscover_tasks(["app.services.ingestion"])

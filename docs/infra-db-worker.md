## Database and worker architecture

### Current local setup

For local development and assessment, the system is intentionally simple:

- **Database**: SQLite file (`app.db`), created automatically in the backend container (or local working directory) on first run.
- **Broker / cache**: Redis (via Docker when using `docker-compose`).
- **Worker**: Celery worker process, running in its own container but sharing the same code and SQLite file as the web API.

This gives you realistic separation of concerns (web vs worker vs broker) while avoiding the overhead of running and managing Postgres locally.

### Roles and responsibilities

#### SQLite database

- **File location**:
  - Local dev (non-Docker): `./app.db` in the project root.
  - Docker (via `docker-compose.yml`): mounted under `/app/data/app.db` using the `app-db` volume.
- **Schema**:
  - `users`: authentication & roles.
  - `creator_profiles`: normalized creators (channels).
  - `content_items`: per-video/per-content records.
  - `content_metrics`: time-based performance snapshots.
  - `ingestion_runs`: run metadata, status, counts, error summaries.
  - `campaigns` + `campaign_members`: campaign definitions and membership.
  - `quota_usage`: YouTube quota tracking.
- **Creation**:
  - On app startup, `app/db/init_db.py` calls `Base.metadata.create_all()` via the async engine.
  - No manual migration needed for local; the DB file is created with the full schema.

#### Redis (broker / backend for Celery)

- **Purpose**:
  - Acts as the **message broker** between web/API and Celery worker.
  - Used as the **result backend** for Celery tasks.
  - Not used for primary data storage; only for task coordination.
- **Configuration**:
  - Controlled by `REDIS_URL` in settings.
  - In local Docker:
    - `REDIS_URL=redis://redis:6379/0` (defined in `docker-compose.yml`).
  - In code:
    - `app/core/config.py` maps `REDIS_URL` to `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` via a post-init validator.

#### Celery worker

- **Location**: `app/core/celery_app.py` (app), `app/services/ingestion/tasks.py` (tasks).
- **Responsibilities**:
  - Execute ingestion runs asynchronously so that:
    - The web API can respond quickly to a “Sync now” request.
    - Long-running work (fetching metrics for multiple channels) doesn’t block HTTP threads.
  - Update `ingestion_runs` status and metrics (counts, duration) even across process boundaries.
- **Configuration**:
  - `celery_app` is created with:
    - `broker=settings.CELERY_BROKER_URL`
    - `backend=settings.CELERY_RESULT_BACKEND`
  - Basic settings:
    - `task_track_started=True`
    - `task_time_limit=3600` (1 hour max).
    - `worker_prefetch_multiplier=1`, `task_acks_late=True` to avoid over-buffering.
    - `broker_connection_retry_on_startup=True`.
- **Task flow**:
  - Web/API creates an `IngestionRun` and, if Redis/Celery are reachable, calls:
    - `run_ingestion_task.delay(run_id, request.model_dump())`.
  - Celery worker receives this and calls `_execute_ingestion()` which:
    - Rehydrates an `IngestionRunRequest`.
    - Opens a DB session (`AsyncSessionLocal`) and calls `IngestionOrchestrator.run()`.
    - Logs success or failure and uses a “failsafe” to mark the run FAILED if an exception escapes.

### Scaling considerations

While the current assessment setup is local and SQLite-based, the architecture is designed to scale with minimal conceptual changes.

#### Web API

- **Scale up**:
  - Behind a real deployment (e.g. a PaaS or Kubernetes), you’d typically:
    - Move from SQLite → Postgres (change `DATABASE_URL`).
    - Run multiple API instances (horizontal scaling).
  - The API itself uses async SQLAlchemy and is stateless (auth via JWT), which is friendly to scaling out.

#### Database

- **Scaling beyond SQLite**:
  - For production, you’d:
    - Point `DATABASE_URL` at Postgres (e.g. `postgresql+asyncpg://...`).
    - Keep the same models and repos; the code is already written to support both SQLite and Postgres.
  - Advantages:
    - Better concurrent write handling.
    - More robust query capabilities (especially with JSONB).
  - Migration strategy:
    - Initialize schema on Postgres with `init_db.py`.
    - Backfill existing data if needed (for local → cloud migration).

#### Redis and Celery

- **Scaling Celery workers**:
  - It’s safe to run multiple Celery workers connected to the same Redis broker:
    - Tasks will be distributed across workers.
    - This allows ingestion to scale horizontally by adding more worker processes.
  - You can adjust:
    - Instance size (CPU/RAM) for workers independently from web.
    - The number of workers per queue.

- **Scaling Redis**:
  - For larger production loads, you can:
    - Increase memory and connection limits.
    - Move to a managed Redis offering with high availability.
  - In the architecture here, Redis load is modest (task dispatch + results), so a small instance is typically enough.

### Flexibility for future deployments

The current infra design deliberately separates:

- **Web service**: Handles HTTP, auth, dashboards, and orchestration of ingest triggers.
- **Worker service**: Handles long-running ingestion/ETL tasks.
- **Data store**: Holds persistent state (creators, content, metrics, campaigns).
- **Broker**: Coordinates async work.

This separation provides:

- **Independent scaling**:
  - Scale workers when ingestion load grows.
  - Scale web when API traffic grows.
  - Scale DB and Redis as storage/coordination needs increase.
- **Clear failure domains**:
  - A worker crash does not crash the web API.
  - Redis issues degrade async ingestion but can fall back to FastAPI `BackgroundTasks` in a pinch.
- **Adaptable deployment story**:
  - Local: SQLite + Redis + Celery via Docker Compose.
  - Cloud (future): Postgres + managed Redis + web + worker each as their own service with appropriate autoscaling.

For this assessment, reviewers get the benefits of a production-style architecture but with a lightweight and reproducible local stack.


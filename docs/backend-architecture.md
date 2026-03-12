## Backend architecture

### High-level layout

- `app/main.py`: FastAPI app factory, CORS, global exception handlers, route wiring, and startup hook (`lifespan`) which initializes the DB and cleans up stale ingestion runs.
- `app/core/`: Cross-cutting concerns.
  - `config.py`: Central configuration using Pydantic Settings (env-driven: `DATABASE_URL`, `YOUTUBE_API_KEY`, `REDIS_URL`, `SECRET_KEY`, etc.).
  - `logging.py`: `setup_logging()` + `get_logger()` to get module-scoped loggers.
  - `celery_app.py`: Celery instance configured from settings (broker/result backend via `REDIS_URL`).
  - `enums.py`, `constants.py`, `exceptions.py`: Shared enums, constants, and domain-specific exceptions.
- `app/db/`:
  - `session.py`: Builds the async engine / `AsyncSessionLocal` with SQLite and Postgres support.
  - `init_db.py`: Runs `Base.metadata.create_all()` and a small set of one-off migrations / backfills; on SQLite this creates `app.db` automatically on first run.
  - `base.py`: Declares `Base` for SQLAlchemy models.
- `app/models/`: ORM models for all core entities:
  - `user`, `creator_profile`, `content_item`, `content_metric`, `ingestion_run`, `campaign`, `campaign_member`, `quota_usage`, etc.
- `app/repos/`: Repository layer (data access abstraction).
  - `base_repo.py`: Base class holding the `AsyncSession`.
  - `creator/`, `content/`, `metric/`, `ingestion_run/`, `campaign/`, `analytics/`: Typed repos for specific aggregates.
- `app/routes/`: HTTP API surface.
  - `auth.py`, `creators.py`, `content.py`, `ingestion.py`, `analytics.py`, `campaigns.py`, `platform.py`, `admin.py`, `health.py`.
  - Each route module is thin: it handles HTTP concerns, auth, and delegates work to services/repos.
- `app/services/`: Application-level orchestration and domain logic.
  - `ingestion/`: YouTube adapter(s), orchestrator, Celery tasks, quota tracking, registry, and validators.
  - `analytics/`: Creator/content analytics aggregation.
  - `platform_service.py`: Platform metadata APIs.
- `app/schemas/`: Pydantic models for I/O contracts (requests/responses).
- `app/utils/`: Shared utilities (datetime helpers, math utils, error mapping).

This structure keeps HTTP, business logic, and persistence concerns separated, and makes it easy to extend both the ingestion pipeline and the API surface without cross-cutting changes.

### Ingestion pipeline: phases and responsibilities

The ingestion pipeline is implemented as a sequence of well-defined phases coordinated by the `IngestionOrchestrator`:

1. **Trigger & dispatch**
   - `app/routes/ingestion.py` exposes `/api/ingestion/run`.
   - `dispatch_ingestion()` (`app/services/ingestion/sync_runner.py`):
     - Creates an `IngestionRun` row via `IngestionRunWriteRepo`.
     - Tries to send the work to Celery (using `celery_app`).
     - If Celery/Redis are unavailable, falls back to a FastAPI `BackgroundTasks` worker in the same process.

2. **Task execution (Celery or background)**
   - Celery worker entry point: `run_ingestion_task` in `app/services/ingestion/tasks.py`.
   - Background path: `_do_background_sync()` in `sync_runner.py`.
   - Both call `IngestionOrchestrator.run()` with the same `IngestionRunRequest` and `run_id`.

3. **Orchestration (`IngestionOrchestrator`)**
   - Located in `app/services/ingestion/orchestrator.py`.
   - Key steps:
     1. **Cleanup**: `cleanup_stale_runs()` marks old PENDING/RUNNING runs as FAILED before starting a new run (protects against ghost runs).
     2. **Prepare run**: Mark the run as RUNNING.
     3. **Resolve channel set**:
        - If `request.channel_ids` is `None`, it looks up the calling user’s tracked channels (via `CreatorReadRepo`).
     4. **Adapter lookup**:
        - Uses `IngestionAdapterRegistry` to find the correct adapter class for `(platform, source_type)`.
     5. **Phase 0 – Data fetch**:
        - Calls `adapter.ingest(channel_ids=...)` which returns a payload of:
          - `creators`: creator snapshots.
          - `content_items`: per-video metadata.
          - `metric_snapshots`: time-based performance metrics.
        - All records go through validators (`validate_creator_record`, `validate_content_record`, `validate_metric_record`) to ensure invariants and guard against malformed data.
     6. **Phase 1 – Creator upsert**:
        - Transforms validated creators into rows and calls `CreatorWriteRepo.bulk_upsert_creators()`.
        - Re-queries all creators for the platform to build a `platform_creator_id -> internal_id` map.
     7. **Phase 2 – Content upsert**:
        - Uses the creator map to attach content items to creators.
        - Calls `ContentWriteRepo.bulk_upsert_content_items()`, then re-queries content items to build a `platform_content_id -> internal_id` map.
     8. **Phase 3 – Metric upsert**:
        - Uses the content map to attach metric snapshots to content items.
        - Calls `MetricWriteRepo.bulk_upsert_metric_snapshots()`.
     9. **Finalize run**:
        - Updates counts and marks the run as SUCCESS with duration and error/warning metrics via `IngestionRunWriteRepo`.
   - Any unhandled exception during the phases rolls back the DB transaction and marks the run as FAILED (`IngestionError`), with a summary for downstream debugging.

### How to add a new platform (e.g. TikTok)

Adding a new platform is a matter of implementing a new adapter and wiring it into the registry; the orchestrator and repos remain unchanged.

1. **Define/enhance enums**
   - In `app/core/enums.py`, ensure there is a value for the new platform:
     - `PlatformEnum.TIKTOK = "tiktok"` (for example).
   - Add any specific `SourceTypeEnum` values if needed (e.g. API, file, webhook).

2. **Create an adapter implementation**
   - Add a new file under `app/services/ingestion/`, e.g. `tiktok_api_adapter.py`.
   - Implement a class matching the base adapter contract from `base_adapter.py`:
     - A public `ingest(channel_ids: list[str]) -> IngestionPayload` method which:
       - Calls the external API(s).
       - Normalizes raw data into the generic payload structure:
         - `creators`, `content_items`, `metric_snapshots` with fields expected by validators.
   - Reuse the same validators where possible; if platform-specific fields differ, extend validators or add new optional fields to the schemas.

3. **Register the adapter**
   - In `app/services/ingestion/registry.py`, register the new adapter:
     - Map `(platform="tiktok", source_type="api")` to `TikTokAPIAdapter`.
   - The orchestrator will automatically pick up the correct adapter based on `IngestionRunRequest.platform` and `.source_type`.

4. **Expose routes (optional)**
   - If you want API consumers to explicitly trigger TikTok runs:
     - Extend `IngestionRunRequest` (Pydantic) if necessary to support TikTok-specific parameters.
     - Ensure frontend uses `platform="tiktok"` when appropriate.

Because all downstream layers (repos, analytics) operate on a normalized schema, adding a new platform is primarily an adapter concern; most of the ingestion pipeline does not need to change.

### How to add a new ingestion mode

Ingestion “modes” can be understood as **source types**: API polling, file ingestion, or even events from a queue. To add a new mode:

1. **Extend the source-type enum**
   - Add a new `SourceTypeEnum` value in `app/core/enums.py`, e.g. `FILE` or `WEBHOOK`.

2. **Define/implement an adapter for that mode**
   - Similar to adding a new platform, implement an adapter that knows how to get and normalize data from the new source:
     - A file-based adapter might parse CSV or JSON dropped into a directory or an S3 bucket.
     - A webhook adapter might interpret batched events.

3. **Update the registry mapping**
   - In `IngestionAdapterRegistry`, create an entry like `(platform="youtube", source_type="file") -> YouTubeFileAdapter`.

4. **Triggering the mode**
   - Extend `IngestionRunRequest` to allow the frontend/admin to choose the new mode:
     - e.g. `source_type="file"` and additional parameters like `file_path` or `batch_id`.
   - Update the route or admin endpoint that constructs the `IngestionRunRequest` to set the new `source_type`.

The orchestrator itself doesn’t change; it only needs a valid adapter implementation for the `(platform, source_type)` pair.

### Error handling and observability

- **Errors**:
  - Domain-level ingestion errors raise `IngestionError` which are turned into run-status FAILED records with summaries.
  - API-level errors raise `AppError` or standard FastAPI/HTTP exceptions; these are mapped in `app/utils/errors.py`.
  - A global exception handler in `app/main.py` catches unhandled exceptions and returns a generic 500 while logging the stack trace.
- **Logging**:
  - All ingestion phases log milestone messages (start/end of phases, map sizes, success/failure).
  - Auth and campaign flows log high-level actions (signup/login, campaign creates/updates).
  - Celery worker logs task start/failure and uses a “failsafe” to mark runs FAILED when exceptions occur.

With this architecture, extending the system to more platforms or ingestion modes is additive: you introduce new adapters and routes, while the orchestration, repositories, and data model remain stable.


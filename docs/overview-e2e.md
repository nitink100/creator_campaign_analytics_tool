## End-to-end overview

### Problem and audience

Brand partnership and creator teams need a reliable way to:

- Discover relevant creators.
- Track their performance across content.
- Group them into campaigns.
- Make data-backed decisions about who to work with.

This project is a small but complete slice of such a platform, focused on YouTube as the initial data source, with an architecture ready to add more platforms later.

### End-to-end user journey

1. **Sign up & sign in**
   - A new user signs up via the frontend.
   - The backend creates a `User` record and returns a JWT access token.
   - The frontend stores the token and uses it for all subsequent API calls.

2. **Discover creators**
   - The user navigates to the Channel Discovery area.
   - They can:
     - Resolve a handle/URL/keyword into a specific YouTube channel (`/api/ingestion/channels/resolve`).
     - Search channels by keyword (`/api/ingestion/channels/search`) with quota-aware safeguards.
   - The system calls YouTube Data API v3 via the YouTube adapter, normalizes the data, and returns consistent preview objects for the UI.

3. **Track creators**
   - When the user decides to track a creator:
     - The frontend calls `/api/ingestion/channels/track`.
     - The backend:
       - Runs a “mini-sync” for the requested channel (via the ingestion orchestrator).
       - Saves/updates the `creator_profile`, `content_items`, and `content_metrics`.
       - Adds an entry to `user_tracked_creators` so this user now “owns” that creator in their workspace.

4. **Analyze performance (Creator Dashboard)**
   - The Creator Leaderboard view calls analytics endpoints to:
     - Fetch aggregated metrics per creator (views, engagement, content counts).
     - Filter by time window (e.g. last N days).
   - The analytics services read from normalized tables and compute:
     - Summary KPIs (e.g. total creators, average engagement).
     - Ranked lists of top creators and top content.
   - This gives the user a quick understanding of who is performing well.

5. **Create and manage campaigns**
   - The user creates campaigns via `/api/campaigns`:
     - Campaigns are scoped to the user and stored with optional metadata (budget, dates, description).
   - They then add tracked creators as campaign members:
     - The API validates that each creator is already tracked by the user.
     - Memberships are stored in `campaign_members`.
   - The UI surfaces campaigns with their creators, so users can manage groups of creators for specific initiatives.

6. **Refresh data (“Sync now”)**
   - At any time, the user can trigger a sync (globally or per creator, depending on the UI action).
   - The ingestion pipeline:
     - Records a new `ingestion_run` and dispatches it to Celery (or falls back to a background task).
     - The orchestrator fetches data from YouTube, upserts creators/content/metrics, and updates run status.
   - The Creator Dashboard and Campaign views automatically reflect the latest metrics, since analytics are computed from the underlying normalized tables.

### End-to-end data flow

1. **Frontend → Backend**
   - All calls route through the API client (`frontend/src/api/client.js`):
     - Attaches JWT token.
     - Uses `VITE_API_URL` to reach the FastAPI backend.
   - Auth context ensures only logged-in users can access protected views and endpoints.

2. **Backend → YouTube API**
   - Ingestion adapters encapsulate calls to YouTube Data API v3.
   - Responses are normalized into generic creator/content/metric payloads, insulated from API quirks.

3. **Persistence**
   - Normalized schema in SQLite (or Postgres if enabled):
     - One row per creator, per content item, per metric snapshot, per run.
   - Repositories abstract data access for creators, content, metrics, and analytics.

4. **Async processing**
   - Celery workers (or FastAPI background tasks) perform long-running ingestion.
   - Redis brokers tasks; the DB stores results and run metadata.

5. **Analytics**
   - Analytics services compute:
     - Aggregations per creator and per content item.
     - Time-windowed views and summaries.
   - Results are served via dedicated analytics routes to keep concerns separate from ingestion logic.

### Extensibility and impact

The architecture is intentionally modular:

- **New platforms**:
  - Add an adapter + registry entry; rest of the pipeline (orchestrator, repos, analytics) remains stable.
- **New ingestion modes**:
  - Add a new `source_type` and adapter (file-based, webhook-based, etc.).
  - Trigger via the same `IngestionRunRequest` and orchestration flow.
- **New analytics views**:
  - Build new analytics services and routes that query the same normalized tables.
  - Add new frontend views that call those endpoints via the shared API client.

For an assessment, this means reviewers see:

- A coherent **user story** from signup through campaigns.
- A realistic **production-style architecture** (web + worker + DB + broker).
- A design that is ready to grow beyond YouTube into multi-platform creator analytics without a rewrite.


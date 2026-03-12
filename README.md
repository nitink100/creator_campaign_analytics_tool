# Creator Campaign Analytics Tool 🚀

A lightweight, high-performance analytics platform for brand partnership teams to track creator performance across platforms (starting with YouTube).

---

## 🏗 End-to-end architecture (high level)

- **Backend** (`app/`):
  - FastAPI + async SQLAlchemy + Pydantic-based settings.
  - Clean layering:
    - `routes/` expose HTTP endpoints.
    - `services/` implement orchestration (ingestion, analytics).
    - `repos/` encapsulate DB reads/writes against normalized models in `models/`.
  - Ingestion pipeline:
    - `IngestionOrchestrator` coordinates phases:
      - Phase 0: fetch from platform adapters (e.g. YouTube).
      - Phase 1: upsert creators.
      - Phase 2: upsert content items.
      - Phase 3: upsert metric snapshots.
    - Adapters are registered in a central registry so adding a new platform or source type is additive.

- **Frontend** (`frontend/`):
  - React + Vite.
  - `AuthContext` manages JWT-based auth and session.
  - A single API client (`src/api/client.js`) centralizes `VITE_API_URL`, error handling, and token injection.
  - Key flows:
    - Creator Dashboard / Leaderboard (analytics views).
    - Channel Discovery & tracking.
    - Campaign creation and membership management.

- **Infra / workers**:
  - Local default: SQLite DB (`app.db`), Redis (broker), Celery worker.
  - Web and worker share the same DB schema; ingestion runs are dispatched via Celery when available, with a background-task fallback if Redis is down.

For deeper details, see:

- Backend architecture: `docs/backend-architecture.md`
- Frontend architecture: `docs/frontend-architecture.md`
- DB + worker architecture: `docs/infra-db-worker.md`
- End-to-end flow and user journey: `docs/overview-e2e.md`

---

## 🛠 Tech Stack

- **Backend**: Python 3.11, FastAPI, SQLAlchemy, Pydantic (Settings & Validation), HTTPX (Async HTTP).
- **Frontend**: React 19, Vite, Chart.js (Visualizations).
- **Database**: SQLite (Local development).
- **Testing**: PyTest (Mocked API calls for 100% deterministic CI/CD).

---

## 🚀 Run Locally in < 5 Minutes

### 1. Prerequisites
- Python 3.11+
- Node.js 18+

### 2. Setup Backend
```bash
cd CreatorCampaignAnalyticsTool
python -m venv venv
source venv/bin/activate  # Mac/Linux
pip install -r requirements.txt
cp .env.example .env      
uvicorn app.main:app --reload --port 8000
```

### 3. Setup Frontend
```bash
cd frontend
npm install
npm run dev
```
Visit `http://localhost:5173` to see the dashboard.

By default the backend uses a local SQLite file (`app.db`), so you **do not** need Postgres for local testing.

### 4. Sync: With or Without Celery
- **Without Redis/Celery**: Sync Now uses FastAPI BackgroundTasks (same process). No extra setup; sync runs in the background after you click Sync Now.
- **With Redis + Celery** (optional): For a dedicated worker process, install Redis, set `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` in `.env`, then run the worker with the same env as the API:  
  `celery -A app.core.celery_app worker -l info`  
  Use the same `DATABASE_URL` and `YOUTUBE_API_KEY` as the API so the worker commits run status to the same DB.

### 5. Run with Docker Compose (backend + Celery worker + Redis)

One image is used for both the API and the Celery worker; the worker runs as a **separate container** (background worker).

```bash
# From repo root
cp .env.example .env   # set YOUTUBE_API_KEY (and optionally SECRET_KEY)
docker compose up --build backend redis celery-worker
```

- **backend**: FastAPI at `http://localhost:8000`
- **celery-worker**: Celery worker (same image, `celery -A app.core.celery_app worker -l info`)
- **redis**: Redis at `localhost:6379`

Web and worker share the same SQLite DB via a volume (`app-db`). To run only the API (no worker): `docker compose up backend redis`.

---

## 🚀 Optional: Deploy on Render (backend + Celery + Redis + Postgres)

The repo includes a **Render Blueprint** (`render.yaml`) that deploys:

- **Web**: FastAPI (Docker)
- **Worker**: Celery (same Docker image, separate service)
- **Redis**: Render Key Value (separate service; Celery broker/backend)
- **PostgreSQL**: Render Postgres (separate database)

**Best practice:** Web, worker, Redis, and DB each run as their own service so you can scale and debug independently.

### Steps

1. Push this repo to GitHub and connect it to [Render](https://render.com).
2. Create a **New Blueprint Instance** and point it at this repo. Render will create the database, Redis, web service, and worker from `render.yaml`.
3. Set **YOUTUBE_API_KEY** on both the web and worker services (Dashboard → each service → Environment).
4. **SECRET_KEY**: The web service gets an auto-generated one. Copy that value and set the same **SECRET_KEY** on the worker service (or use a Render [Environment Group](https://render.com/docs/environment-groups) and attach it to both).
5. Your API URL will be `https://creatorcampaign-api.onrender.com` (or the name you give it). Point your frontend (e.g. Vercel) at this URL for the API.

### Optional: REDIS_URL

The app uses **REDIS_URL** when set (for Celery broker and result backend). The blueprint wires Render’s Redis to **REDIS_URL** automatically. Locally you can set `REDIS_URL` or `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` in `.env`.

**Already have Web + Postgres?** To add Redis and the Celery worker only, see [docs/RENDER_CELERY_REDIS.md](docs/RENDER_CELERY_REDIS.md).

---

## 📊 Data Sources & Tradeoffs

### Data Source: YouTube Data API v3
We chose the official API over scraping to ensure long-term stability and respect for platform terms. We ingest:
- **Channel Metadata**: Subscriber counts and branding.
- **Content Metrics**: Views, Likes, and Comment counts per video.

### Tradeoffs & Decisions
1. **Aggressive Ingestion Cap**: We initially capped at 20 videos to save API quota during dev, but bumped to 100 for "Production" depth.
2. **SQLite**: Used for easy local execution. In a real media enterprise, we would use Postgres for its superior JSONB performance and concurrent write handling.
3. **Manual vs Auto Sync**: We implemented a "Sync Now" trigger in the UI for immediate feedback, but the backend is wired for 6-hour cron syncs via configuration.

---

## 🚀 What I'd Build With Another Week

1. **Social expansion**: Dedicated adapters for TikTok and Instagram using the same normalized schema, so a partnership team can compare creators across platforms in one view.
2. **Richer bulk ingestion**: Move fully to database-native upserts (`INSERT ... ON CONFLICT` in Postgres, batched merges) and introduce back-pressure controls so we can safely ingest thousands of creators/videos per run.
3. **Deeper campaign analytics**: Add campaign-level metrics (e.g. reach, engagement, cost-per-view/engagement) by tying creator/content performance to simple spend inputs, plus campaign comparison views.
4. **Alerting and insights**: Build an “insights” layer that surfaces opinionated signals — e.g. creators whose engagement has dropped X% week-over-week, campaigns with high spend but low lift, or videos that are quietly outperforming a creator’s baseline.
5. **Production-grade infra**: Swap SQLite for Postgres by default, add environment-specific configs, and ship a one-click cloud deployment (web + worker + Postgres + Redis) with autoscaling workers.
6. **UX polish and onboarding**: Add an in-app onboarding tour, saved views/filters for power users, and a “sample data” mode so non-technical stakeholders can explore the product without creating a YouTube API key.

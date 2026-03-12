## How to run the project (local)

This guide walks you from cloning the repo to running the **backend**, **frontend**, **Redis**, and **Celery worker** locally.

You do **not** need Postgres for local testing; the backend uses SQLite by default.

---

### 1. Clone the repository

```bash
git clone https://github.com/your-org/creator_campaign_analytics_tool.git
cd creator_campaign_analytics_tool
```

Replace the URL above with your actual Git remote if different.

---

### 2. Backend: run with Python (no Docker)

This is the simplest way to explore the backend.

#### 2.1. Create and activate a virtualenv

```bash
python -m venv .venv
source .venv/bin/activate  # Mac/Linux
# On Windows (PowerShell): .venv\Scripts\Activate.ps1
```

#### 2.2. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### 2.3. Configure environment

```bash
cp .env.example .env
```

Then edit `.env`:

- Set `YOUTUBE_API_KEY` to a valid YouTube Data API v3 key.
- Optionally adjust:
  - `APP_ENV=local`
  - `DATABASE_URL=sqlite:///./app.db` (default; no change needed for local).
  - `LOG_LEVEL=INFO` (or `DEBUG` while developing).

#### 2.4. Start the backend

```bash
uvicorn app.main:app --reload --port 8000
```

Check:

- Health: `http://localhost:8000/health`
- API docs: `http://localhost:8000/docs`

On first startup, `app.db` and all tables will be created automatically.

---

### 3. Frontend: run with Vite dev server

In a new terminal (backend still running):

```bash
cd frontend
npm install
```

Optionally create `frontend/.env.local`:

```bash
VITE_API_URL=http://localhost:8000
```

Then start the dev server:

```bash
npm run dev
```

Open the URL shown in the terminal (typically `http://localhost:5173`).

You should be able to:

- Sign up with an email and password.
- Log in and see the dashboard.
- Discover creators and track them.
- Create campaigns and add tracked creators.

---

### 4. Full local stack with Docker Compose (backend + Redis + Celery)

If you have Docker Desktop installed and running, you can spin up the backend, Redis, and Celery worker with one command.

From the repo root:

#### 4.1. Prepare `.env`

```bash
cp .env.example .env
```

Edit `.env`:

- Set `YOUTUBE_API_KEY` to your API key.
- Optionally set `SECRET_KEY` to a long random string (JWT signing key).

#### 4.2. Start services

```bash
docker compose up --build backend redis celery-worker
```

This will start:

- `backend` at `http://localhost:8000`
- `redis` at `localhost:6379`
- `celery-worker` (no port; logs stream in the terminal)

Check:

- API docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`

The SQLite DB file is stored in the `app-db` Docker volume and shared between web and worker.

#### 4.3. Frontend with Docker stack

With Docker running the backend, start the frontend the same way as above:

```bash
cd frontend
npm install
npm run dev
```

Ensure `VITE_API_URL` points to `http://localhost:8000`.

---

### 5. Quick smoke test checklist

1. Start backend (Python or Docker) and confirm `http://localhost:8000/docs` loads.
2. Start frontend (`npm run dev`) and open the Vite dev URL (e.g. `http://localhost:5173`).
3. In the UI:
   - Sign up with a new email and password.
   - Log in with the same credentials.
   - Discover a YouTube channel (via handle/URL or search).
   - Track that creator.
   - Create a campaign and add the tracked creator as a member.
   - Trigger “Sync now” and wait for ingestion to complete.
4. Refresh the dashboard and confirm creator metrics are visible and updated.

If all of these steps work, the end-to-end system is functioning as intended.


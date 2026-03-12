# Deploy Celery + Redis on Render (with existing Web + Postgres)

Use these steps when you already have the **Web Service** and **PostgreSQL** on Render and want to add **Redis** and the **Celery worker**.

---

## 1. Create Redis (Key Value)

1. In Render Dashboard: **New +** → **Redis** (or **Key Value**).
2. **Name:** e.g. `creatorcampaign-redis`.
3. **Region:** Same as your web service (e.g. Oregon).
4. **Plan:** Free (or Starter if you need more).
5. **Create Redis**.
6. After it’s created, open the Redis service and copy the **Internal Connection URL** (or **Connection String**). It looks like:
   `rediss://red-xxxx:port` or `redis://...`
   You’ll use this as `REDIS_URL` for both the web and the worker.

---

## 2. Point the Web Service at Redis

1. Open your **Web Service** (e.g. `creator_campaign_analytics_tool`).
2. **Environment** → **Add Environment Variable**:
   - **Key:** `REDIS_URL`
   - **Value:** paste the Redis **Internal Connection URL** from step 1.
3. Save. Render will redeploy the web service.  
   The app uses `REDIS_URL` for Celery broker/backend when set, so “Sync now” will start using Celery once the worker is running.

---

## 3. Create the Celery Background Worker

1. **New +** → **Background Worker**.
2. **Connect repository:** same GitHub repo as your web service.
3. **Name:** e.g. `creatorcampaign-celery`.
4. **Region:** Same as web and Redis.
5. **Branch:** `main` (or your default).
6. **Runtime:** **Docker**.
7. **Dockerfile Path:** `./Dockerfile` (repo root).
8. **Docker Context:** `.` (or leave default).
9. **Start Command (override):**
   ```bash
   celery -A app.core.celery_app worker -l info
   ```
   This overrides the image’s default CMD so the container runs the worker instead of uvicorn.
10. **Instance type:** Free (or same as your web service if you prefer).

---

## 4. Worker environment variables

Add the **same** env vars the web service uses (same values where possible), so the worker can talk to Postgres and Redis:

| Key             | Where to get it |
|-----------------|------------------|
| `DATABASE_URL`  | Copy from your **PostgreSQL** service (Internal Database URL). Same value as on the web service. |
| `REDIS_URL`     | Copy from your **Redis** service (Internal Connection URL). Same value as on the web service. |
| `SECRET_KEY`    | Copy the **exact same** value from your **Web Service** env. Required for consistency (e.g. if any code uses it). |
| `YOUTUBE_API_KEY` | Same as on the web service (so the worker can run sync jobs that use the API). |
| `APP_ENV`       | `production` (optional). |

**Important:** `SECRET_KEY` on the worker must match the web service. Copy it from the web service’s Environment tab.

---

## 5. Deploy and verify

1. **Create Background Worker** (or Save if editing). Render will build the same Docker image and run the worker with the start command above.
2. After deploy, open the worker **Logs**. You should see something like:
   - `celery@... ready.`
   - `Connected to redis://...`
3. In your app’s UI, use **Sync now**. The job should be handled by the worker (check worker logs for task received/completed).

---

## Summary

| Service            | Type              | Role |
|--------------------|-------------------|------|
| Existing Web       | Web Service       | Serves API; dispatches sync to Celery when `REDIS_URL` is set. |
| Existing Postgres  | PostgreSQL        | Shared DB for web and worker. |
| New Redis          | Redis (Key Value) | Celery broker and result backend. |
| New Worker         | Background Worker | Runs `celery -A app.core.celery_app worker -l info`; same image as web. |

If you prefer to define everything in code (including Redis and worker), use the repo’s **Blueprint** (`render.yaml`) for a new stack; for an existing web + Postgres, the steps above are the right approach.

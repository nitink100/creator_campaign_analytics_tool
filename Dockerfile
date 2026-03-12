# Single image for both FastAPI web and Celery worker (same codebase, different start command).
# Best practice: run Redis and Postgres as separate services; web and worker as two services using this image.

FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY app/ ./app/
COPY seed_channels.json ./
# For docker-compose: shared DB dir so web and worker can use same SQLite file
RUN mkdir -p /app/data

# Render sets PORT; default for local Docker
ENV PORT=8000
EXPOSE 8000

# Default: run web server. Override in Render for worker: celery -A app.core.celery_app worker -l info
# Render sets PORT at runtime; shell form so ${PORT} is expanded.
CMD sh -c 'uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}'

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    APP_NAME: str = "Creator Analytics Platform"
    APP_ENV: str = "local"

    DATABASE_URL: str = "sqlite:///./app.db"

    LOG_LEVEL: str = "INFO"

    YOUTUBE_API_KEY: str = ""

    ENABLE_CRON_SYNC: bool = True
    CRON_SCHEDULE: str = "0 */6 * * *"

    ALLOW_MANUAL_SYNC: bool = True

    YOUTUBE_MAX_CHANNELS_PER_RUN: int = 25
    YOUTUBE_MAX_VIDEOS_PER_CHANNEL: int = 100

    SEED_CHANNEL_IDS_FILE: str = "seed_channels.json"

    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # Auth (set SECRET_KEY in production)
    SECRET_KEY: str = "dev-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120  # 2 hours (default session)
    STAY_SIGNED_IN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days when "Stay signed in" is used

    # First admin: signup with this email gets role=admin (optional)
    ADMIN_EMAIL: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
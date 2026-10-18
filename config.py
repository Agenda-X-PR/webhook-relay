"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration for the webhook relay service."""

    # Service
    app_name: str = "webhook-relay"
    version: str = "0.1.0"

    # Database
    database_url: str = "sqlite:///./webhooks.db"

       # Retry behavior
    max_attempts: int = 5
    base_retry_delay_seconds: int = 30  # 30s, 60s, 120s, 240s, 480s

    # Worker
    worker_poll_interval_seconds: int = 5
    
    # Security (per-provider secrets will come later)
    webhook_secret: str = "change-me-in-production"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
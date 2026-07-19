from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    worker_name: str = "tradepilot-worker"
    log_level: str = "INFO"
    worker_poll_interval_seconds: int = Field(default=5, ge=1)
    database_url: str = "postgresql+asyncpg://tradepilot:change_me@localhost:5432/tradepilot"

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
    storage_root: str = "storage/local"
    prompts_root: str = "/app/prompts/production/v1"

    gemini_api_key: str = ""
    gemini_model: str = "models/gemini-2.0-flash"
    gemini_timeout_seconds: int = Field(default=120, ge=1)
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-chat"
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_timeout_seconds: int = Field(default=120, ge=1)
    provider_order: str = "gemini"

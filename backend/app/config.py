from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    api_host: str = "127.0.0.1"
    api_port: int = Field(default=8000, ge=1, le=65535)
    log_level: str = "INFO"

    database_url: str = (
        "postgresql+asyncpg://tradepilot:change_me@localhost:5432/tradepilot"
    )
    database_sync_url: str = (
        "postgresql+psycopg://tradepilot:change_me@localhost:5432/tradepilot"
    )
    db_pool_size: int = Field(default=5, ge=1)
    db_max_overflow: int = Field(default=10, ge=0)
    db_pool_timeout_seconds: int = Field(default=30, ge=1)
    db_pool_recycle_seconds: int = Field(default=1800, ge=1)
    db_echo: bool = False
    schema_package_root: str = "schemas/production/v1"

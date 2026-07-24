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

    database_url: str = "postgresql+asyncpg://tradepilot:change_me@localhost:5432/tradepilot"
    database_sync_url: str = "postgresql+psycopg://tradepilot:change_me@localhost:5432/tradepilot"
    db_pool_size: int = Field(default=5, ge=1)
    db_max_overflow: int = Field(default=10, ge=0)
    db_pool_timeout_seconds: int = Field(default=30, ge=1)
    db_pool_recycle_seconds: int = Field(default=1800, ge=1)
    db_echo: bool = False
    schema_package_root: str = "schemas/production/v1"
    storage_root: str = "storage/local"
    max_upload_size_bytes: int = Field(default=10485760, ge=1)
    auth_cookie_name: str = "tradepilot_session"
    auth_session_lifetime_seconds: int = Field(default=86400 * 7, ge=1)
    auth_cookie_secure: bool = Field(default=False)

    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash"
    gemini_timeout_seconds: int = Field(default=120, ge=1)
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-chat"
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_timeout_seconds: int = Field(default=120, ge=1)
    provider_order: str = "gemini"

    # ---- Security (TP-1604) ----
    allowed_hosts: list[str] = Field(default=["*"])
    cors_origins: list[str] = Field(default=["*"])
    enable_https_redirect: bool = False

    rate_limit_enabled: bool = False
    rate_limit_requests: int = Field(default=60, ge=1)
    rate_limit_window_seconds: int = Field(default=60, ge=1)
    login_rate_limit_requests: int = Field(default=5, ge=1)
    login_rate_limit_window_seconds: int = Field(default=60, ge=1)

    csrf_enabled: bool = False
    csrf_exclude_paths: list[str] = Field(
        default=[
            "/health",
            "/health/ready",
            "/health/schema-registry",
            "/health/worker",
            "/api/auth/login",
        ]
    )

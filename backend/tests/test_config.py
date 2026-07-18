import pytest

from app.config import AppConfig

_CONFIG_VARS = [
    "APP_ENV",
    "API_HOST",
    "API_PORT",
    "LOG_LEVEL",
    "DATABASE_URL",
    "DATABASE_SYNC_URL",
    "DB_POOL_SIZE",
    "DB_MAX_OVERFLOW",
    "DB_POOL_TIMEOUT_SECONDS",
    "DB_POOL_RECYCLE_SECONDS",
    "DB_ECHO",
    "GEMINI_API_KEY",
    "DEEPSEEK_API_KEY",
]


def _clear_config_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in _CONFIG_VARS:
        monkeypatch.delenv(var, raising=False)


def test_dev_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_config_env(monkeypatch)
    config = AppConfig()
    assert config.app_env == "development"
    assert config.api_host == "127.0.0.1"
    assert config.api_port == 8000
    assert config.log_level == "INFO"


def test_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_config_env(monkeypatch)
    monkeypatch.setenv("API_HOST", "0.0.0.0")
    monkeypatch.setenv("API_PORT", "9000")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    config = AppConfig()
    assert config.api_host == "0.0.0.0"
    assert config.api_port == 9000
    assert config.log_level == "DEBUG"


def test_app_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_config_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("API_HOST", "0.0.0.0")
    config = AppConfig()
    assert config.app_env == "test"
    assert config.api_host == "0.0.0.0"
    assert config.api_port == 8000


def test_invalid_port_rejected() -> None:
    try:
        AppConfig(api_port=-1)
    except Exception:
        return
    raise AssertionError("Expected ValidationError for port -1")


def test_missing_ai_keys_do_not_block(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_config_env(monkeypatch)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    config = AppConfig()
    assert config.app_env == "development"

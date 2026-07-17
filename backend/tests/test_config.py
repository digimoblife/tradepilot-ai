import pytest

from app.config import AppConfig


def test_dev_defaults() -> None:
    config = AppConfig()
    assert config.app_env == "development"
    assert config.api_host == "127.0.0.1"
    assert config.api_port == 8000
    assert config.log_level == "INFO"


def test_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_HOST", "0.0.0.0")
    monkeypatch.setenv("API_PORT", "9000")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    config = AppConfig()
    assert config.api_host == "0.0.0.0"
    assert config.api_port == 9000
    assert config.log_level == "DEBUG"


def test_invalid_port_rejected() -> None:
    try:
        AppConfig(api_port=-1)
    except Exception:
        return
    raise AssertionError("Expected ValidationError for port -1")


def test_missing_ai_keys_do_not_block(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    config = AppConfig()
    assert config.app_env == "development"

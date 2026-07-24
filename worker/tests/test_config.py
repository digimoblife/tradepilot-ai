import pytest

from app.config import WorkerConfig


def test_defaults() -> None:
    config = WorkerConfig()
    assert config.app_env == "development"
    assert config.worker_name == "tradepilot-worker"
    assert config.log_level == "INFO"
    assert config.worker_poll_interval_seconds == 5
    assert config.gemini_model == "gemini-3.5-flash"
    assert config.provider_order == "gemini"


def test_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("WORKER_NAME", "test-worker")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("WORKER_POLL_INTERVAL_SECONDS", "10")
    config = WorkerConfig()
    assert config.app_env == "production"
    assert config.worker_name == "test-worker"
    assert config.log_level == "DEBUG"
    assert config.worker_poll_interval_seconds == 10


def test_zero_poll_interval_rejected() -> None:
    with pytest.raises(Exception):
        WorkerConfig(worker_poll_interval_seconds=0)


def test_negative_poll_interval_rejected() -> None:
    with pytest.raises(Exception):
        WorkerConfig(worker_poll_interval_seconds=-1)


def test_missing_credentials_do_not_block(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    config = WorkerConfig()
    assert config.app_env == "development"

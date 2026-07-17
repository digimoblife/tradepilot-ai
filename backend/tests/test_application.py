from fastapi import FastAPI

from app.application import create_application


def test_create_application_returns_fastapi_instance() -> None:
    app = create_application()
    assert isinstance(app, FastAPI), f"Expected FastAPI instance, got {type(app)}"


def test_application_title() -> None:
    app = create_application()
    assert app.title == "TradePilot AI", f"Expected 'TradePilot AI', got '{app.title}'"


def test_application_version_defined() -> None:
    app = create_application()
    assert app.version != "", "Application version must not be empty"


def test_independent_instances() -> None:
    app1 = create_application()
    app2 = create_application()
    assert app1 is not app2, "Repeated factory calls must create independent instances"

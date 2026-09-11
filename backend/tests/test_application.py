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


def test_v1_routes_unmounted_and_v2_routes_present() -> None:
    from fastapi.routing import _IncludedRouter

    app = create_application()
    paths: set[str] = set()
    for r in app.routes:
        if isinstance(r, _IncludedRouter):
            for sub_r in r.original_router.routes:
                path = getattr(sub_r, "path", None)
                if path:
                    paths.add(path)

    # Legacy V1 prefixes must NOT be registered
    assert not any(p.startswith("/api/trade-sessions") for p in paths)
    assert not any(p.startswith("/api/analyses") for p in paths)
    assert not any(p.startswith("/api/analysis-jobs") for p in paths)
    assert not any(p.startswith("/api/actions") for p in paths)
    assert not any(p.startswith("/api/evidence") for p in paths)

    # Active core and V2 routes MUST be registered
    assert "/health" in paths
    assert "/health/ready" in paths
    assert "/api/auth/login" in paths
    assert "/api/v2/trade-sessions" in paths
    assert "/api/sessions/{session_id}/workspace" in paths
    assert "/api/evaluation-records" in paths

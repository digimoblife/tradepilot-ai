from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app import __version__
from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.routes.analyses import analysis_router
from app.api.routes.analyses import session_router as analysis_session_router
from app.api.routes.analysis_jobs import router as analysis_jobs_router
from app.api.routes.context import router as context_router
from app.api.routes.evidence import evidence_router
from app.api.routes.evidence import session_router as evidence_session_router
from app.api.routes.timeline import router as timeline_router
from app.api.routes.trade_actions import router as trade_actions_router
from app.api.routes.trade_sessions import router as trade_sessions_router
from app.auth.errors import (
    AUTHENTICATION_INACTIVE,
    AuthenticationError,
)
from app.config import AppConfig
from app.logging import configure_logging
from app.schemas.manifest import load_production_manifest
from app.schemas.registry import LocalSchemaRegistry


def create_application() -> FastAPI:
    config = AppConfig()
    configure_logging(config.log_level)

    app = FastAPI(
        title="TradePilot AI",
        version=__version__,
    )

    # Load and validate production schema manifest + registry on startup
    package_root = Path(config.schema_package_root)
    manifest = load_production_manifest(package_root)
    registry = LocalSchemaRegistry(manifest, package_root)
    app.state.schema_manifest = manifest
    app.state.schema_registry = registry

    @app.exception_handler(AuthenticationError)
    async def auth_error_handler(request, exc: AuthenticationError) -> JSONResponse:
        if exc.code == AUTHENTICATION_INACTIVE:
            return JSONResponse(
                status_code=403,
                content={"detail": "Account is not active", "code": exc.code},
            )
        return JSONResponse(
            status_code=401,
            content={"detail": exc.message or "Authentication failed", "code": exc.code},
        )

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(evidence_session_router)
    app.include_router(evidence_router)
    app.include_router(analysis_session_router)
    app.include_router(analysis_router)
    app.include_router(analysis_jobs_router)
    app.include_router(context_router)
    app.include_router(timeline_router)
    app.include_router(trade_actions_router)
    app.include_router(trade_sessions_router)

    return app

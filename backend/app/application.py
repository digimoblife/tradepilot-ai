from pathlib import Path

from fastapi import FastAPI

from app import __version__
from app.api.auth import router as auth_router
from app.api.exception_handlers import register_handlers
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
from app.config import AppConfig
from app.logging import configure_logging, get_logger
from app.schemas.manifest import load_production_manifest
from app.schemas.registry import LocalSchemaRegistry


log = get_logger(__name__)


def create_application() -> FastAPI:
    config = AppConfig()
    configure_logging(config.log_level)
    log.info("Backend application starting", extra={"env": config.app_env, "log_level": config.log_level})

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

    # Register centralized exception handlers (TP-1007)
    register_handlers(app)

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

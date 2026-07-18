from pathlib import Path

from fastapi import FastAPI

from app import __version__
from app.api.health import router as health_router
from app.config import AppConfig
from app.logging import configure_logging
from app.schemas.manifest import load_production_manifest


def create_application() -> FastAPI:
    config = AppConfig()
    configure_logging(config.log_level)

    app = FastAPI(
        title="TradePilot AI",
        version=__version__,
    )

    # Load and validate production schema manifest on startup
    package_root = Path(config.schema_package_root)
    manifest = load_production_manifest(package_root)
    app.state.schema_manifest = manifest

    app.include_router(health_router)

    return app

from fastapi import FastAPI

from app import __version__
from app.api.health import router as health_router
from app.config import AppConfig
from app.logging import configure_logging


def create_application() -> FastAPI:
    config = AppConfig()
    configure_logging(config.log_level)

    app = FastAPI(
        title="TradePilot AI",
        version=__version__,
    )

    app.include_router(health_router)

    return app

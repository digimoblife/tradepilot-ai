from pathlib import Path

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app import __version__
from app.api.auth import router as auth_router
from app.api.exception_handlers import register_handlers
from app.api.health import router as health_router
from app.api.routes.evaluation import router as evaluation_router
from app.api.routes.market_evidence import router as market_evidence_router
from app.api.security import (
    CSRFProtectionMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
)
from app.config import AppConfig
from app.logging import configure_logging, get_logger
from app.trade_workspace.api.routes.trade_sessions import router as rebuild_trade_sessions_router

log = get_logger(__name__)


def create_application() -> FastAPI:
    config = AppConfig()
    configure_logging(config.log_level)
    log.info(
        "Backend application starting",
        extra={"env": config.app_env, "log_level": config.log_level},
    )

    app = FastAPI(
        title="TradePilot AI",
        version=__version__,
        max_body_size=config.max_upload_size_bytes,
    )

    # ---- Security middleware (TP-1604) ----

    # Trusted hosts
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=config.allowed_hosts,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Security headers (always applied)
    app.add_middleware(SecurityHeadersMiddleware)

    # CSRF protection (conditionally enabled via config)
    app.add_middleware(CSRFProtectionMiddleware, config=config)

    # Rate limiting (conditionally enabled via config)
    app.add_middleware(RateLimitMiddleware, config=config)

    # HTTPS redirect (production only)
    if config.enable_https_redirect:
        app.add_middleware(HTTPSRedirectMiddleware)

    # Register centralized exception handlers (TP-1007)
    register_handlers(app)

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(market_evidence_router)
    app.include_router(rebuild_trade_sessions_router)
    app.include_router(evaluation_router)

    return app

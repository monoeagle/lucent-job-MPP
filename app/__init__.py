import logging
import os

from flask import Flask

from app.core.config import Config
from app.core.errors import register_error_handlers
from app.core.middleware import register_middleware

logger = logging.getLogger(__name__)


def create_app(config_overrides: dict | None = None) -> Flask:
    app = Flask(__name__)

    config = _build_config(config_overrides)
    app.config.from_mapping(
        AUTH_MODE=config.AUTH_MODE,
        ENV=config.ENV,
        JWT_SECRET=config.JWT_SECRET,
        STUB_TOKEN_TTL_SECONDS=config.STUB_TOKEN_TTL_SECONDS,
        DATABASE_URL=config.DATABASE_URL,
    )

    register_middleware(app)
    register_error_handlers(app)

    from app.api.v1 import health
    app.register_blueprint(health.bp)

    from app.api.v1 import auth
    app.register_blueprint(auth.bp)

    return app


def _build_config(overrides: dict | None) -> Config:
    original_env = {}
    if overrides:
        for key, value in overrides.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = str(value)
    try:
        return Config()
    finally:
        if overrides:
            for key, original in original_env.items():
                if original is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = original

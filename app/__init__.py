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
        CMDB_MODE=config.CMDB_MODE,
        CMDB_STUB_DATA_PATH=config.CMDB_STUB_DATA_PATH,
    )

    register_middleware(app)
    register_error_handlers(app)

    from app.data.db.session import get_engine, get_session_factory
    engine = get_engine(app.config["DATABASE_URL"])
    app.session_factory = get_session_factory(engine)

    @app.before_request
    def open_session():
        from flask import g
        g.db_session = app.session_factory()

    @app.teardown_appcontext
    def close_session(exception=None):
        from flask import g
        session = g.pop("db_session", None)
        if session is not None:
            session.close()

    # CMDB client
    if app.config.get("CMDB_MODE") == "stub":
        from app.data.clients.cmdb_client import CmdbStubClient
        app.cmdb_client = CmdbStubClient(
            data_path=app.config.get("CMDB_STUB_DATA_PATH", "./stubs/cmdb/")
        )

    from app.api.v1 import health
    app.register_blueprint(health.bp)

    from app.api.v1 import auth
    app.register_blueprint(auth.bp)

    from app.api.v1 import catalog
    app.register_blueprint(catalog.bp)
    app.register_blueprint(catalog.admin_bp)

    from app.api.v1 import orders
    app.register_blueprint(orders.bp)

    from app.api.v1 import cmdb
    app.register_blueprint(cmdb.bp)

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

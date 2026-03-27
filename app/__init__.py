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
        GITLAB_URL=config.GITLAB_URL,
        GITLAB_TOKEN=config.GITLAB_TOKEN,
        GITLAB_PROJECT_ID=config.GITLAB_PROJECT_ID,
        APPROVAL_DEFAULT_DEADLINE_HOURS=config.APPROVAL_DEFAULT_DEADLINE_HOURS,
        APPROVAL_ALLOW_SELF_APPROVAL=config.APPROVAL_ALLOW_SELF_APPROVAL,
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

    from app.api.v1 import context
    app.register_blueprint(context.bp)
    app.register_blueprint(context.admin_bp)

    from app.api.v1 import provisioning
    app.register_blueprint(provisioning.bp)
    app.register_blueprint(provisioning.admin_bp)

    from app.api.v1 import approvals
    app.register_blueprint(approvals.admin_bp)
    app.register_blueprint(approvals.approvals_bp)

    from app.api.v1 import admin
    app.register_blueprint(admin.bp)

    # GitLab client
    if app.config.get("GITLAB_URL"):
        from app.data.clients.gitlab_client import GitLabClient
        app.gitlab_client = GitLabClient(
            base_url=app.config["GITLAB_URL"],
            token=app.config.get("GITLAB_TOKEN", ""),
            project_id=int(app.config.get("GITLAB_PROJECT_ID", "1")),
        )

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

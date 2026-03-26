# Phase 0+1: Scaffold + Auth-Stub + Error-Patterns — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Set up a Flask project with PostgreSQL, JWT-based auth-stub, standardized error handling, and a pytest test harness — the foundation for all subsequent phases.

**Architecture:** Flask app factory pattern with Clean Architecture layers (api → services → domain ← data). Auth is pluggable via AUTH_MODE env var. All error responses follow a unified JSON format with request_id tracking.

**Tech Stack:** Python 3.11+, Flask, SQLAlchemy, Alembic, PyJWT, pytest, PostgreSQL

---

## File Structure

```
lucent-app-mpp-TDD/
├── app/
│   ├── __init__.py              # Flask app factory
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py            # Configuration from env vars
│   │   ├── errors.py            # Error classes + error handler registration
│   │   └── middleware.py         # Request-ID middleware
│   ├── domain/
│   │   ├── __init__.py
│   │   └── auth.py              # User dataclass, role constants
│   ├── services/
│   │   ├── __init__.py
│   │   └── auth_service.py      # Auth logic (stub + interface for LDAP)
│   └── api/
│       ├── __init__.py
│       └── v1/
│           ├── __init__.py
│           ├── auth.py           # Login + stub-users endpoints
│           └── health.py         # Health check endpoint
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Shared fixtures, test app, test client
│   ├── unit/
│   │   ├── __init__.py
│   │   └── test_auth_service.py
│   └── integration/
│       ├── __init__.py
│       ├── test_health.py
│       ├── test_auth_login.py
│       ├── test_auth_stub_users.py
│       └── test_error_handling.py
├── migrations/                   # Alembic (created by alembic init)
├── requirements.txt
├── pytest.ini
└── .env.example
```

---

### Task 1: Project Dependencies

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `pytest.ini`

- [ ] **Step 1: Create requirements.txt**

```
flask==3.1.0
sqlalchemy==2.0.36
alembic==1.14.1
psycopg2-binary==2.9.10
pyjwt==2.10.1
python-dotenv==1.0.1
```

- [ ] **Step 2: Create .env.example**

```
AUTH_MODE=stub
ENV=development
JWT_SECRET=stub-jwt-secret-dev-only
STUB_TOKEN_TTL_SECONDS=86400
DATABASE_URL=postgresql://mpp:mpp@localhost:5432/mpp_dev
TEST_DATABASE_URL=postgresql://mpp:mpp@localhost:5432/mpp_test
```

- [ ] **Step 3: Create pytest.ini**

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
addopts = -v --tb=short
```

- [ ] **Step 4: Install dependencies**

Run: `pip install -r requirements.txt && pip install pytest`
Expected: All packages installed successfully

- [ ] **Step 5: Commit**

```bash
git init
git add requirements.txt .env.example pytest.ini
git commit -m "chore: add project dependencies and pytest config"
```

---

### Task 2: Configuration Module

**Files:**
- Create: `app/__init__.py`
- Create: `app/core/__init__.py`
- Create: `app/core/config.py`
- Test: `tests/unit/test_config.py`

- [ ] **Step 1: Write the failing test**

Create `tests/__init__.py` (empty), `tests/unit/__init__.py` (empty), then:

```python
# tests/unit/test_config.py
import os
import pytest


class TestConfig:
    def test_default_auth_mode_is_ldap(self, monkeypatch):
        monkeypatch.delenv("AUTH_MODE", raising=False)
        from app.core.config import get_config
        config = get_config()
        assert config.AUTH_MODE == "ldap"

    def test_stub_auth_mode(self, monkeypatch):
        monkeypatch.setenv("AUTH_MODE", "stub")
        monkeypatch.setenv("ENV", "development")
        from app.core.config import get_config
        config = get_config()
        assert config.AUTH_MODE == "stub"

    def test_stub_in_production_raises(self, monkeypatch):
        monkeypatch.setenv("AUTH_MODE", "stub")
        monkeypatch.setenv("ENV", "production")
        from app.core.config import get_config
        with pytest.raises(RuntimeError, match="must not be used in production"):
            get_config()

    def test_invalid_auth_mode_raises(self, monkeypatch):
        monkeypatch.setenv("AUTH_MODE", "invalid")
        from app.core.config import get_config
        with pytest.raises(ValueError, match="Unknown AUTH_MODE"):
            get_config()

    def test_jwt_secret_fallback_in_stub_mode(self, monkeypatch):
        monkeypatch.setenv("AUTH_MODE", "stub")
        monkeypatch.setenv("ENV", "development")
        monkeypatch.delenv("JWT_SECRET", raising=False)
        from app.core.config import get_config
        config = get_config()
        assert config.JWT_SECRET == "stub-jwt-secret-dev-only"

    def test_stub_token_ttl_default(self, monkeypatch):
        monkeypatch.setenv("AUTH_MODE", "stub")
        monkeypatch.setenv("ENV", "development")
        from app.core.config import get_config
        config = get_config()
        assert config.STUB_TOKEN_TTL_SECONDS == 86400

    def test_database_url_from_env(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/testdb")
        from app.core.config import get_config
        config = get_config()
        assert config.DATABASE_URL == "postgresql://test:test@localhost/testdb"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_config.py -v`
Expected: FAIL — ModuleNotFoundError: No module named 'app'

- [ ] **Step 3: Write minimal implementation**

```python
# app/__init__.py
```

```python
# app/core/__init__.py
```

```python
# app/core/config.py
import os
import logging

logger = logging.getLogger(__name__)

VALID_AUTH_MODES = ("stub", "ldap")


class Config:
    def __init__(self):
        self.AUTH_MODE = os.environ.get("AUTH_MODE", "ldap")
        self.ENV = os.environ.get("ENV", "development")
        self.JWT_SECRET = os.environ.get("JWT_SECRET", "")
        self.STUB_TOKEN_TTL_SECONDS = int(
            os.environ.get("STUB_TOKEN_TTL_SECONDS", "86400")
        )
        self.DATABASE_URL = os.environ.get(
            "DATABASE_URL", "postgresql://mpp:mpp@localhost:5432/mpp_dev"
        )

        self._validate()

    def _validate(self):
        if self.AUTH_MODE not in VALID_AUTH_MODES:
            raise ValueError(
                f"Unknown AUTH_MODE value: {self.AUTH_MODE}. "
                f"Allowed: {', '.join(VALID_AUTH_MODES)}"
            )

        if self.AUTH_MODE == "stub" and self.ENV == "production":
            raise RuntimeError(
                "FATAL: AUTH_MODE=stub must not be used in production environment. "
                "Aborting."
            )

        if self.AUTH_MODE == "stub" and not self.JWT_SECRET:
            self.JWT_SECRET = "stub-jwt-secret-dev-only"
            logger.warning(
                "JWT_SECRET not set in stub mode. Using fallback secret. "
                "Never use this in production."
            )


def get_config() -> Config:
    return Config()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_config.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add app/ tests/
git commit -m "feat: add configuration module with auth-mode validation"
```

---

### Task 3: Domain — User Model and Role Constants

**Files:**
- Create: `app/domain/__init__.py`
- Create: `app/domain/auth.py`
- Test: `tests/unit/test_domain_auth.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_domain_auth.py
from app.domain.auth import User, Role


class TestRole:
    def test_role_values(self):
        assert Role.REQUESTER == "requester"
        assert Role.APPROVER == "approver"
        assert Role.ADMIN == "admin"


class TestUser:
    def test_create_user(self):
        user = User(
            username="test-requester",
            display_name="Test Requester",
            email="requester@test.local",
            roles=[Role.REQUESTER],
        )
        assert user.username == "test-requester"
        assert user.roles == ["requester"]

    def test_user_has_role(self):
        user = User(
            username="test-multi",
            display_name="Test Multi",
            email="multi@test.local",
            roles=[Role.REQUESTER, Role.APPROVER],
        )
        assert user.has_role(Role.REQUESTER) is True
        assert user.has_role(Role.ADMIN) is False

    def test_user_is_admin(self):
        admin = User(
            username="test-admin",
            display_name="Test Admin",
            email="admin@test.local",
            roles=[Role.ADMIN],
        )
        assert admin.is_admin is True

    def test_user_to_jwt_claims(self):
        user = User(
            username="test-requester",
            display_name="Test Requester",
            email="requester@test.local",
            roles=[Role.REQUESTER],
        )
        claims = user.to_jwt_claims()
        assert claims["sub"] == "test-requester"
        assert claims["roles"] == ["requester"]
        assert claims["email"] == "requester@test.local"
        assert claims["display_name"] == "Test Requester"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_domain_auth.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Write minimal implementation**

```python
# app/domain/__init__.py
```

```python
# app/domain/auth.py
from dataclasses import dataclass, field


class Role:
    REQUESTER = "requester"
    APPROVER = "approver"
    ADMIN = "admin"


@dataclass(frozen=True)
class User:
    username: str
    display_name: str
    email: str
    roles: list[str] = field(default_factory=list)

    def has_role(self, role: str) -> bool:
        return role in self.roles

    @property
    def is_admin(self) -> bool:
        return self.has_role(Role.ADMIN)

    def to_jwt_claims(self) -> dict:
        return {
            "sub": self.username,
            "roles": self.roles,
            "email": self.email,
            "display_name": self.display_name,
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_domain_auth.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add app/domain/ tests/unit/test_domain_auth.py
git commit -m "feat: add User domain model and Role constants"
```

---

### Task 4: Auth Service — Stub Implementation

**Files:**
- Create: `app/services/__init__.py`
- Create: `app/services/auth_service.py`
- Test: `tests/unit/test_auth_service.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_auth_service.py
import pytest
import jwt
from app.services.auth_service import AuthService


class TestAuthServiceStub:
    def setup_method(self):
        self.service = AuthService(
            auth_mode="stub",
            jwt_secret="test-secret",
            token_ttl_seconds=3600,
        )

    def test_login_valid_user(self):
        result = self.service.login("test-requester", "stub-password")
        assert result["user"]["username"] == "test-requester"
        assert result["user"]["roles"] == ["requester"]
        assert "token" in result
        assert "expires_at" in result

    def test_login_without_password(self):
        result = self.service.login("test-requester", "")
        assert result["user"]["username"] == "test-requester"

    def test_login_with_none_password(self):
        result = self.service.login("test-requester", None)
        assert result["user"]["username"] == "test-requester"

    def test_login_unknown_user(self):
        with pytest.raises(AuthService.InvalidCredentialsError):
            self.service.login("unknown-user", "stub-password")

    def test_login_multi_role_user(self):
        result = self.service.login("test-multi", "stub-password")
        assert set(result["user"]["roles"]) == {"requester", "approver"}

    def test_token_contains_correct_claims(self):
        result = self.service.login("test-admin", "stub-password")
        decoded = jwt.decode(
            result["token"], "test-secret", algorithms=["HS256"]
        )
        assert decoded["sub"] == "test-admin"
        assert decoded["roles"] == ["admin"]
        assert decoded["email"] == "admin@test.local"
        assert decoded["display_name"] == "Test Admin"
        assert "iat" in decoded
        assert "exp" in decoded

    def test_verify_token_valid(self):
        result = self.service.login("test-requester", "stub-password")
        user = self.service.verify_token(result["token"])
        assert user.username == "test-requester"

    def test_verify_token_expired(self):
        service = AuthService(
            auth_mode="stub", jwt_secret="test-secret", token_ttl_seconds=-1
        )
        result = service.login("test-requester", "stub-password")
        with pytest.raises(AuthService.TokenExpiredError):
            service.verify_token(result["token"])

    def test_verify_token_invalid_signature(self):
        result = self.service.login("test-requester", "stub-password")
        with pytest.raises(AuthService.InvalidTokenError):
            wrong_secret_service = AuthService(
                auth_mode="stub", jwt_secret="wrong-secret", token_ttl_seconds=3600
            )
            wrong_secret_service.verify_token(result["token"])

    def test_get_stub_users(self):
        users = self.service.get_stub_users()
        assert len(users) == 4
        usernames = [u["username"] for u in users]
        assert "test-requester" in usernames
        assert "test-approver" in usernames
        assert "test-admin" in usernames
        assert "test-multi" in usernames
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_auth_service.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Write minimal implementation**

```python
# app/services/__init__.py
```

```python
# app/services/auth_service.py
from datetime import datetime, timedelta, timezone

import jwt

from app.domain.auth import User, Role

STUB_USERS = [
    User(
        username="test-requester",
        display_name="Test Requester",
        email="requester@test.local",
        roles=[Role.REQUESTER],
    ),
    User(
        username="test-approver",
        display_name="Test Approver",
        email="approver@test.local",
        roles=[Role.APPROVER],
    ),
    User(
        username="test-admin",
        display_name="Test Admin",
        email="admin@test.local",
        roles=[Role.ADMIN],
    ),
    User(
        username="test-multi",
        display_name="Test Multi Role",
        email="multi@test.local",
        roles=[Role.REQUESTER, Role.APPROVER],
    ),
]

_STUB_USER_MAP = {u.username: u for u in STUB_USERS}


class AuthService:
    class InvalidCredentialsError(Exception):
        pass

    class TokenExpiredError(Exception):
        pass

    class InvalidTokenError(Exception):
        pass

    def __init__(self, auth_mode: str, jwt_secret: str, token_ttl_seconds: int):
        self.auth_mode = auth_mode
        self.jwt_secret = jwt_secret
        self.token_ttl_seconds = token_ttl_seconds

    def login(self, username: str, password: str | None) -> dict:
        if self.auth_mode == "stub":
            return self._stub_login(username)
        raise NotImplementedError("LDAP auth not implemented yet")

    def _stub_login(self, username: str) -> dict:
        user = _STUB_USER_MAP.get(username)
        if user is None:
            raise self.InvalidCredentialsError("invalid credentials")

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=self.token_ttl_seconds)

        claims = user.to_jwt_claims()
        claims["iat"] = now
        claims["exp"] = expires_at

        token = jwt.encode(claims, self.jwt_secret, algorithm="HS256")

        return {
            "token": token,
            "user": {
                "username": user.username,
                "display_name": user.display_name,
                "email": user.email,
                "roles": list(user.roles),
            },
            "expires_at": expires_at.isoformat().replace("+00:00", "Z"),
        }

    def verify_token(self, token: str) -> User:
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            raise self.TokenExpiredError("token expired")
        except jwt.InvalidTokenError:
            raise self.InvalidTokenError("invalid token")

        return User(
            username=payload["sub"],
            display_name=payload["display_name"],
            email=payload["email"],
            roles=payload["roles"],
        )

    def get_stub_users(self) -> list[dict]:
        return [
            {
                "username": u.username,
                "display_name": u.display_name,
                "email": u.email,
                "roles": list(u.roles),
                "hint": "Use for self-approval tests"
                if u.username == "test-multi"
                else "Login without password or use 'stub-password'",
            }
            for u in STUB_USERS
        ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_auth_service.py -v`
Expected: 11 passed

- [ ] **Step 5: Commit**

```bash
git add app/services/ tests/unit/test_auth_service.py
git commit -m "feat: add AuthService with stub login and JWT token generation"
```

---

### Task 5: Error Handling — Standard Error Format + Middleware

**Files:**
- Create: `app/core/errors.py`
- Create: `app/core/middleware.py`
- Test: `tests/integration/test_error_handling.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/integration/__init__.py
```

```python
# tests/integration/test_error_handling.py
import json
import pytest
from app import create_app


@pytest.fixture
def app():
    app = create_app({"AUTH_MODE": "stub", "ENV": "development", "TESTING": True})
    return app


@pytest.fixture
def client(app):
    return app.test_client()


class TestErrorFormat:
    def test_404_returns_standard_format(self, client):
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == 404
        data = response.get_json()
        assert "error_code" in data
        assert "message" in data
        assert "request_id" in data
        assert data["error_code"] == "NOT_FOUND"

    def test_response_has_request_id_header(self, client):
        response = client.get("/api/v1/nonexistent")
        assert "X-Request-ID" in response.headers
        data = response.get_json()
        assert response.headers["X-Request-ID"] == data["request_id"]

    def test_success_response_has_request_id_header(self, client):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers

    def test_405_returns_standard_format(self, client):
        response = client.put("/api/v1/health")
        assert response.status_code == 405
        data = response.get_json()
        assert data["error_code"] == "METHOD_NOT_ALLOWED"

    def test_validation_error_format(self, client):
        response = client.post(
            "/api/v1/auth/login",
            json={},
            content_type="application/json",
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data["error_code"] == "VALIDATION_FAILED"
        assert "request_id" in data
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_error_handling.py -v`
Expected: FAIL — ImportError: cannot import name 'create_app'

- [ ] **Step 3: Write implementation**

```python
# app/core/errors.py
from flask import jsonify, request


class AppError(Exception):
    def __init__(self, error_code: str, message: str, status_code: int = 400,
                 details: dict | None = None):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class ValidationError(AppError):
    def __init__(self, message: str, details: dict | None = None):
        super().__init__("VALIDATION_FAILED", message, 400, details)


class NotFoundError(AppError):
    def __init__(self, message: str, details: dict | None = None):
        super().__init__("NOT_FOUND", message, 404, details)


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Nicht authentifiziert."):
        super().__init__("UNAUTHORIZED", message, 401)


class ForbiddenError(AppError):
    def __init__(self, message: str = "Keine Berechtigung."):
        super().__init__("FORBIDDEN", message, 403)


class ConflictError(AppError):
    def __init__(self, message: str, details: dict | None = None):
        super().__init__("CONFLICT", message, 409, details)


def _error_response(error_code: str, message: str, status_code: int,
                    details: dict | None = None):
    request_id = getattr(request, "request_id", "unknown")
    body = {
        "error_code": error_code,
        "message": message,
        "details": details,
        "request_id": request_id,
    }
    return jsonify(body), status_code


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(error):
        return _error_response(
            error.error_code, error.message, error.status_code, error.details
        )

    @app.errorhandler(404)
    def handle_404(error):
        return _error_response("NOT_FOUND", "Die angeforderte Ressource wurde nicht gefunden.", 404)

    @app.errorhandler(405)
    def handle_405(error):
        return _error_response("METHOD_NOT_ALLOWED", "Diese HTTP-Methode ist nicht erlaubt.", 405)

    @app.errorhandler(500)
    def handle_500(error):
        app.logger.error("Unhandled error: %s", error, exc_info=True)
        return _error_response(
            "INTERNAL_ERROR", "Ein interner Serverfehler ist aufgetreten.", 500
        )
```

```python
# app/core/middleware.py
import uuid

from flask import request, g


def register_middleware(app):
    @app.before_request
    def set_request_id():
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.request_id = request_id
        g.request_id = request_id

    @app.after_request
    def add_request_id_header(response):
        request_id = getattr(request, "request_id", "unknown")
        response.headers["X-Request-ID"] = request_id
        return response
```

Now update `app/__init__.py` to be the app factory:

```python
# app/__init__.py
import logging

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
    import os
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
```

- [ ] **Step 4: (Defer — needs blueprints from Task 6)**

This task's tests depend on the health and auth blueprints which are created in Task 6. Continue to Task 6, then come back.

- [ ] **Step 5: Commit (after Task 6)**

```bash
git add app/core/errors.py app/core/middleware.py app/__init__.py tests/integration/
git commit -m "feat: add standard error handling, request-ID middleware, and app factory"
```

---

### Task 6: API Blueprints — Health + Auth Endpoints

**Files:**
- Create: `app/api/__init__.py`
- Create: `app/api/v1/__init__.py`
- Create: `app/api/v1/health.py`
- Create: `app/api/v1/auth.py`
- Test: `tests/integration/test_health.py`
- Test: `tests/integration/test_auth_login.py`
- Test: `tests/integration/test_auth_stub_users.py`

- [ ] **Step 1: Write failing tests for health endpoint**

```python
# tests/integration/test_health.py
import pytest
from app import create_app


@pytest.fixture
def client():
    app = create_app({"AUTH_MODE": "stub", "ENV": "development", "TESTING": True})
    return app.test_client()


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_health_returns_status_ok(self, client):
        response = client.get("/api/v1/health")
        data = response.get_json()
        assert data["status"] == "ok"
        assert "auth_mode" in data
```

- [ ] **Step 2: Write failing tests for auth login**

```python
# tests/integration/test_auth_login.py
import pytest
from app import create_app


@pytest.fixture
def client():
    app = create_app({"AUTH_MODE": "stub", "ENV": "development", "TESTING": True})
    return app.test_client()


class TestAuthLogin:
    def test_login_success(self, client):
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "test-requester", "password": "stub-password"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "token" in data
        assert data["user"]["username"] == "test-requester"
        assert data["user"]["roles"] == ["requester"]
        assert "expires_at" in data

    def test_login_without_password(self, client):
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "test-requester"},
        )
        assert response.status_code == 200

    def test_login_empty_password(self, client):
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "test-requester", "password": ""},
        )
        assert response.status_code == 200

    def test_login_unknown_user(self, client):
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "unknown", "password": "stub-password"},
        )
        assert response.status_code == 401
        data = response.get_json()
        assert data["error_code"] == "INVALID_CREDENTIALS"

    def test_login_missing_username(self, client):
        response = client.post(
            "/api/v1/auth/login",
            json={},
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data["error_code"] == "VALIDATION_FAILED"

    def test_login_response_has_auth_mode_header(self, client):
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "test-requester", "password": "stub-password"},
        )
        assert response.headers.get("X-Auth-Mode") == "stub"

    def test_login_multi_role_user(self, client):
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "test-multi", "password": "stub-password"},
        )
        data = response.get_json()
        assert set(data["user"]["roles"]) == {"requester", "approver"}
```

- [ ] **Step 3: Write failing tests for stub-users endpoint**

```python
# tests/integration/test_auth_stub_users.py
import pytest
from app import create_app


@pytest.fixture
def stub_client():
    app = create_app({"AUTH_MODE": "stub", "ENV": "development", "TESTING": True})
    return app.test_client()


@pytest.fixture
def ldap_client():
    app = create_app({"AUTH_MODE": "ldap", "ENV": "development", "TESTING": True,
                       "JWT_SECRET": "test-secret"})
    return app.test_client()


class TestStubUsersEndpoint:
    def test_stub_users_returns_list(self, stub_client):
        response = stub_client.get("/api/v1/dev/auth/stub-users")
        assert response.status_code == 200
        data = response.get_json()
        assert "stub_users" in data
        assert len(data["stub_users"]) == 4
        assert data["static_password"] == "stub-password"

    def test_stub_users_not_available_in_ldap_mode(self, ldap_client):
        response = ldap_client.get("/api/v1/dev/auth/stub-users")
        assert response.status_code == 404
```

- [ ] **Step 4: Run all tests to verify they fail**

Run: `pytest tests/integration/ -v`
Expected: FAIL — ImportError

- [ ] **Step 5: Implement blueprints**

```python
# app/api/__init__.py
```

```python
# app/api/v1/__init__.py
```

```python
# app/api/v1/health.py
from flask import Blueprint, jsonify, current_app

bp = Blueprint("health", __name__, url_prefix="/api/v1")


@bp.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "ok",
        "auth_mode": current_app.config["AUTH_MODE"],
    })
```

```python
# app/api/v1/auth.py
from flask import Blueprint, jsonify, request, current_app

from app.core.errors import ValidationError, AppError
from app.services.auth_service import AuthService

bp = Blueprint("auth", __name__, url_prefix="/api/v1")


def _get_auth_service() -> AuthService:
    return AuthService(
        auth_mode=current_app.config["AUTH_MODE"],
        jwt_secret=current_app.config["JWT_SECRET"],
        token_ttl_seconds=current_app.config["STUB_TOKEN_TTL_SECONDS"],
    )


@bp.route("/auth/login", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}
    username = body.get("username")
    if not username:
        raise ValidationError("username is required")

    password = body.get("password")
    service = _get_auth_service()

    try:
        result = service.login(username, password)
    except AuthService.InvalidCredentialsError:
        raise AppError("INVALID_CREDENTIALS", "invalid credentials", 401)

    response = jsonify(result)
    if current_app.config["AUTH_MODE"] == "stub":
        response.headers["X-Auth-Mode"] = "stub"
    return response


@bp.route("/dev/auth/stub-users", methods=["GET"])
def stub_users():
    if current_app.config["AUTH_MODE"] != "stub":
        from app.core.errors import NotFoundError
        raise NotFoundError("Die angeforderte Ressource wurde nicht gefunden.")

    service = _get_auth_service()
    users = service.get_stub_users()
    return jsonify({
        "stub_users": users,
        "static_password": "stub-password",
        "note": "Auth-Stub is active. Never use in production.",
    })
```

- [ ] **Step 6: Run ALL tests**

Run: `pytest tests/ -v`
Expected: All tests pass (unit + integration)

- [ ] **Step 7: Commit**

```bash
git add app/api/ app/__init__.py tests/integration/
git commit -m "feat: add health, login, and stub-users API endpoints"
```

---

### Task 7: Auth Middleware — JWT Token Verification for Protected Endpoints

**Files:**
- Create: `app/core/auth.py`
- Modify: `app/api/v1/auth.py` (add token-protected test endpoint)
- Test: `tests/integration/test_auth_middleware.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/integration/test_auth_middleware.py
import pytest
from app import create_app


@pytest.fixture
def app():
    return create_app({"AUTH_MODE": "stub", "ENV": "development", "TESTING": True})


@pytest.fixture
def client(app):
    return app.test_client()


def _get_token(client, username="test-requester"):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "stub-password"},
    )
    return response.get_json()["token"]


class TestAuthMiddleware:
    def test_protected_endpoint_without_token(self, client):
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401
        data = response.get_json()
        assert data["error_code"] == "UNAUTHORIZED"

    def test_protected_endpoint_with_valid_token(self, client):
        token = _get_token(client)
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["username"] == "test-requester"
        assert data["roles"] == ["requester"]

    def test_protected_endpoint_with_invalid_token(self, client):
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401

    def test_protected_endpoint_with_malformed_header(self, client):
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "NotBearer token"},
        )
        assert response.status_code == 401

    def test_admin_only_endpoint_with_requester(self, client):
        token = _get_token(client, "test-requester")
        response = client.get(
            "/api/v1/admin/health",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    def test_admin_only_endpoint_with_admin(self, client):
        token = _get_token(client, "test-admin")
        response = client.get(
            "/api/v1/admin/health",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_auth_middleware.py -v`
Expected: FAIL

- [ ] **Step 3: Implement auth middleware**

```python
# app/core/auth.py
from functools import wraps

from flask import request, g, current_app

from app.core.errors import UnauthorizedError, ForbiddenError
from app.services.auth_service import AuthService


def _get_auth_service() -> AuthService:
    return AuthService(
        auth_mode=current_app.config["AUTH_MODE"],
        jwt_secret=current_app.config["JWT_SECRET"],
        token_ttl_seconds=current_app.config["STUB_TOKEN_TTL_SECONDS"],
    )


def _extract_token() -> str:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise UnauthorizedError("Nicht authentifiziert.")
    return auth_header[7:]


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = _extract_token()
        service = _get_auth_service()
        try:
            user = service.verify_token(token)
        except AuthService.TokenExpiredError:
            raise UnauthorizedError("Token abgelaufen.")
        except AuthService.InvalidTokenError:
            raise UnauthorizedError("Ungültiger Token.")
        g.current_user = user
        return f(*args, **kwargs)
    return decorated


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated(*args, **kwargs):
            user = g.current_user
            if not any(user.has_role(r) for r in roles):
                raise ForbiddenError("Keine Berechtigung.")
            return f(*args, **kwargs)
        return decorated
    return decorator
```

Add `/auth/me` and `/admin/health` endpoints to `app/api/v1/auth.py`:

Append to `app/api/v1/auth.py`:

```python
from app.core.auth import login_required, role_required
from flask import g


@bp.route("/auth/me", methods=["GET"])
@login_required
def me():
    user = g.current_user
    return jsonify({
        "username": user.username,
        "display_name": user.display_name,
        "email": user.email,
        "roles": list(user.roles),
    })


@bp.route("/admin/health", methods=["GET"])
@role_required("admin")
def admin_health():
    return jsonify({"status": "ok", "role": "admin"})
```

- [ ] **Step 4: Run ALL tests**

Run: `pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
git add app/core/auth.py app/api/v1/auth.py tests/integration/test_auth_middleware.py
git commit -m "feat: add JWT auth middleware with login_required and role_required decorators"
```

---

### Task 8: Shared Test Fixtures (conftest.py)

**Files:**
- Create: `tests/conftest.py`
- Modify: All test files to use shared fixtures

- [ ] **Step 1: Create shared conftest.py**

```python
# tests/conftest.py
import pytest
from app import create_app


@pytest.fixture
def app():
    app = create_app({
        "AUTH_MODE": "stub",
        "ENV": "development",
        "TESTING": True,
    })
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_headers(client):
    """Factory fixture: returns auth headers for a given username."""
    def _get_headers(username="test-requester"):
        response = client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": "stub-password"},
        )
        token = response.get_json()["token"]
        return {"Authorization": f"Bearer {token}"}
    return _get_headers


@pytest.fixture
def requester_headers(auth_headers):
    return auth_headers("test-requester")


@pytest.fixture
def approver_headers(auth_headers):
    return auth_headers("test-approver")


@pytest.fixture
def admin_headers(auth_headers):
    return auth_headers("test-admin")
```

- [ ] **Step 2: Remove duplicate fixtures from integration test files**

Remove the `app`, `client`, `stub_client` fixtures from each integration test file that duplicates what's in conftest.py. Keep only test-specific fixtures (like `ldap_client` in `test_auth_stub_users.py`).

- [ ] **Step 3: Run ALL tests**

Run: `pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 4: Commit**

```bash
git add tests/
git commit -m "refactor: extract shared test fixtures to conftest.py"
```

---

### Task 9: Database Setup — SQLAlchemy + Alembic

**Files:**
- Create: `app/data/__init__.py`
- Create: `app/data/db/__init__.py`
- Create: `app/data/db/session.py`
- Create: `alembic.ini` (via alembic init)
- Test: `tests/integration/test_database.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/integration/test_database.py
import pytest
from sqlalchemy import text


class TestDatabaseConnection:
    def test_db_engine_connects(self, app):
        from app.data.db.session import get_engine
        engine = get_engine(app.config["DATABASE_URL"])
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            assert result.scalar() == 1

    def test_db_session_lifecycle(self, app):
        from app.data.db.session import get_session_factory, get_engine
        engine = get_engine(app.config["DATABASE_URL"])
        SessionFactory = get_session_factory(engine)
        session = SessionFactory()
        result = session.execute(text("SELECT 1"))
        assert result.scalar() == 1
        session.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_database.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Implement database session management**

```python
# app/data/__init__.py
```

```python
# app/data/db/__init__.py
```

```python
# app/data/db/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

_engines: dict[str, object] = {}


class Base(DeclarativeBase):
    pass


def get_engine(database_url: str):
    if database_url not in _engines:
        _engines[database_url] = create_engine(database_url, echo=False)
    return _engines[database_url]


def get_session_factory(engine):
    return sessionmaker(bind=engine)
```

Add DATABASE_URL to app config. Update `app/__init__.py` — add this to `create_app` after `app.config.from_mapping(...)`:

```python
    app.config["DATABASE_URL"] = config.DATABASE_URL
```

- [ ] **Step 4: Create test database**

Run: `createdb mpp_test` (or `psql -c "CREATE DATABASE mpp_test;"`)

Update `app/core/config.py` to add:
```python
        self.TEST_DATABASE_URL = os.environ.get(
            "TEST_DATABASE_URL",
            "postgresql://mpp:mpp@localhost:5432/mpp_test",
        )
```

Update `tests/conftest.py` to use TEST_DATABASE_URL:
```python
@pytest.fixture
def app():
    import os
    app = create_app({
        "AUTH_MODE": "stub",
        "ENV": "development",
        "TESTING": True,
        "DATABASE_URL": os.environ.get(
            "TEST_DATABASE_URL",
            "postgresql://mpp:mpp@localhost:5432/mpp_test"
        ),
    })
    yield app
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/integration/test_database.py -v`
Expected: 2 passed

- [ ] **Step 6: Initialize Alembic**

Run: `alembic init migrations`

Edit `alembic.ini` — set `sqlalchemy.url`:
```ini
sqlalchemy.url = postgresql://mpp:mpp@localhost:5432/mpp_dev
```

Edit `migrations/env.py` — add Base metadata import:
```python
from app.data.db.session import Base
target_metadata = Base.metadata
```

- [ ] **Step 7: Commit**

```bash
git add app/data/ alembic.ini migrations/ tests/integration/test_database.py tests/conftest.py app/core/config.py
git commit -m "feat: add SQLAlchemy engine, session management, and Alembic setup"
```

---

### Task 10: Final Verification — Full Test Suite

**Files:** None (verification only)

- [ ] **Step 1: Run complete test suite**

Run: `pytest tests/ -v --tb=short`
Expected: All tests pass (unit + integration)

- [ ] **Step 2: Verify project structure**

Run: `find . -name "*.py" -not -path "./.venv/*" -not -path "./migrations/*" | sort`
Expected output should match the file structure defined at the top of this plan.

- [ ] **Step 3: Verify endpoints manually**

Run: `FLASK_APP=app AUTH_MODE=stub flask run --port 5000`

Then in another terminal:
```bash
# Health check
curl http://localhost:5000/api/v1/health

# Login
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "test-requester", "password": "stub-password"}'

# Stub users
curl http://localhost:5000/api/v1/dev/auth/stub-users

# Protected endpoint (use token from login response)
curl http://localhost:5000/api/v1/auth/me \
  -H "Authorization: Bearer <TOKEN>"
```

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "chore: phase 0+1 complete — scaffold, auth-stub, error handling, database setup"
```

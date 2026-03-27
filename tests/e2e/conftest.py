"""
Shared fixtures for E2E integration tests.
All tests use a real Flask app with a real PostgreSQL test database and no mocks.
"""
import pytest

from app import create_app
from app.data.db.session import get_engine, Base

TEST_DB = "postgresql://mpp:mpp@localhost:5432/mpp_test"

_APP_CONFIG = {
    "AUTH_MODE": "stub",
    "ENV": "development",
    "TESTING": "True",
    "DATABASE_URL": TEST_DB,
    "CMDB_MODE": "stub",
    "CMDB_STUB_DATA_PATH": "./stubs/cmdb/",
}


@pytest.fixture(scope="function")
def e2e_app():
    """
    Creates a fresh Flask app and rebuilds the test database schema for each test function.
    Scope=function ensures full isolation: no shared state between tests.
    """
    app = create_app(_APP_CONFIG)
    engine = get_engine(TEST_DB)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield app, engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def client(e2e_app):
    app, _ = e2e_app
    return app.test_client()


@pytest.fixture
def requester_token(client):
    resp = client.post("/api/v1/auth/login", json={"username": "test-requester"})
    assert resp.status_code == 200, f"Login failed: {resp.get_json()}"
    return resp.get_json()["token"]


@pytest.fixture
def admin_token(client):
    resp = client.post("/api/v1/auth/login", json={"username": "test-admin"})
    assert resp.status_code == 200, f"Login failed: {resp.get_json()}"
    return resp.get_json()["token"]


@pytest.fixture
def approver_token(client):
    resp = client.post("/api/v1/auth/login", json={"username": "test-approver"})
    assert resp.status_code == 200, f"Login failed: {resp.get_json()}"
    return resp.get_json()["token"]


def auth(token: str) -> dict:
    """Liefert Authorization-Header fuer einen gegebenen JWT-Token."""
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Template-Definitionen fuer Test-Seeding
# ---------------------------------------------------------------------------

LINUX_VM = {
    "slug": "vm-linux",
    "version": "1.0.0",
    "type": "vm",
    "display_name": "Linux Virtual Machine",
    "description": "Standard-Linux-VM mit konfigurierbaren Werten.",
    "category": "Compute",
    "tofu_module_source": "git::https://gitlab.internal/tofu-modules/vm-linux.git?ref=v1.0.0",
    "estimated_cost_eur_per_month": 85.00,
    "parameters": [
        {
            "key": "cpu_cores",
            "label": "CPU-Kerne",
            "type": "integer",
            "required": True,
            "tofu_variable_name": "cpu_cores",
            "display_order": 1,
            "group": "Compute",
            "constraints": {"min": 1, "max": 64, "step": 1, "unit": "Kerne"},
            "depends_on": [],
            "affects_options_of": [],
        },
        {
            "key": "ram_gb",
            "label": "RAM",
            "type": "integer",
            "required": True,
            "tofu_variable_name": "ram_gb",
            "display_order": 2,
            "group": "Compute",
            "constraints": {"min": 2, "max": 256, "step": 2, "unit": "GB"},
            "depends_on": [],
            "affects_options_of": [],
        },
        {
            "key": "os_type",
            "label": "Betriebssystem",
            "type": "enum",
            "required": True,
            "tofu_variable_name": "os_type",
            "display_order": 3,
            "group": "System",
            "constraints": {
                "options": [
                    {"value": "ubuntu-22.04", "label": "Ubuntu 22.04 LTS", "enabled": True},
                    {"value": "rhel-9", "label": "RHEL 9", "enabled": True},
                ]
            },
            "depends_on": [],
            "affects_options_of": [],
        },
    ],
}

POSTGRES_DB = {
    "slug": "db-postgres",
    "version": "1.0.0",
    "type": "database",
    "display_name": "PostgreSQL Datenbank",
    "description": "Managed PostgreSQL-Instanz.",
    "category": "Database",
    "tofu_module_source": "git::https://gitlab.internal/tofu-modules/db-postgres.git?ref=v1.0.0",
    "estimated_cost_eur_per_month": 45.00,
    "parameters": [
        {
            "key": "pg_version",
            "label": "Version",
            "type": "enum",
            "required": True,
            "tofu_variable_name": "pg_version",
            "display_order": 1,
            "group": "Datenbank",
            "constraints": {
                "options": [
                    {"value": "15", "label": "PostgreSQL 15", "enabled": True},
                    {"value": "16", "label": "PostgreSQL 16", "enabled": True},
                ]
            },
            "depends_on": [],
            "affects_options_of": [],
        },
        {
            "key": "storage_gb",
            "label": "Speicher",
            "type": "integer",
            "required": True,
            "tofu_variable_name": "storage_gb",
            "display_order": 2,
            "group": "Datenbank",
            "constraints": {"min": 10, "max": 1000, "step": 10, "unit": "GB"},
            "depends_on": [],
            "affects_options_of": [],
        },
    ],
}


@pytest.fixture
def seeded_templates(client, admin_token):
    """Registriert Linux-VM- und PostgreSQL-Templates und gibt deren Antwortdaten zurueck."""
    templates = []
    for tmpl in [LINUX_VM, POSTGRES_DB]:
        resp = client.post(
            "/api/v1/admin/catalog/templates",
            json=tmpl,
            headers=auth(admin_token),
        )
        assert resp.status_code == 201, (
            f"Seeding des Templates '{tmpl['slug']}' fehlgeschlagen: {resp.get_json()}"
        )
        templates.append(resp.get_json())
    return templates

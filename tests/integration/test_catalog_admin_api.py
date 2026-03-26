# tests/integration/test_catalog_admin_api.py
import pytest
from app import create_app
from app.data.db.session import get_engine, get_session_factory, Base


@pytest.fixture
def admin_app():
    app = create_app({
        "AUTH_MODE": "stub", "ENV": "development", "TESTING": "True",
        "DATABASE_URL": "postgresql://mpp:mpp@localhost:5432/mpp_test",
    })
    engine = get_engine(app.config["DATABASE_URL"])
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield app, engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def admin_client(admin_app):
    app, _ = admin_app
    return app.test_client()


@pytest.fixture
def admin_header(admin_client):
    resp = admin_client.post("/api/v1/auth/login", json={"username": "test-admin"})
    return {"Authorization": f"Bearer {resp.get_json()['token']}"}


@pytest.fixture
def requester_header(admin_client):
    resp = admin_client.post("/api/v1/auth/login", json={"username": "test-requester"})
    return {"Authorization": f"Bearer {resp.get_json()['token']}"}


def _valid_template(**overrides):
    t = {
        "slug": "vm-linux",
        "version": "1.0.0",
        "type": "vm",
        "display_name": "Linux VM",
        "description": "A Linux VM.",
        "category": "Compute",
        "tofu_module_source": "git::https://gitlab.internal/tofu/vm.git",
        "parameters": [
            {"key": "cpu", "label": "CPU", "type": "integer", "required": True,
             "tofu_variable_name": "cpu_cores", "display_order": 1,
             "constraints": {"min": 1, "max": 64}}
        ],
    }
    t.update(overrides)
    return t


class TestRegisterTemplate:
    def test_register_success(self, admin_client, admin_header):
        resp = admin_client.post("/api/v1/admin/catalog/templates",
                                  json=_valid_template(), headers=admin_header)
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["slug"] == "vm-linux"
        assert data["status"] == "active"
        assert "id" in data

    def test_register_requires_admin(self, admin_client, requester_header):
        resp = admin_client.post("/api/v1/admin/catalog/templates",
                                  json=_valid_template(), headers=requester_header)
        assert resp.status_code == 403

    def test_register_duplicate_returns_409(self, admin_client, admin_header):
        admin_client.post("/api/v1/admin/catalog/templates",
                           json=_valid_template(), headers=admin_header)
        resp = admin_client.post("/api/v1/admin/catalog/templates",
                                  json=_valid_template(), headers=admin_header)
        assert resp.status_code == 409

    def test_register_validation_error(self, admin_client, admin_header):
        bad = _valid_template(slug="INVALID!")
        resp = admin_client.post("/api/v1/admin/catalog/templates",
                                  json=bad, headers=admin_header)
        assert resp.status_code == 400

    def test_register_no_required_param(self, admin_client, admin_header):
        bad = _valid_template(parameters=[
            {"key": "opt", "label": "Opt", "type": "string", "required": False,
             "tofu_variable_name": "opt", "display_order": 1, "constraints": {}}
        ])
        resp = admin_client.post("/api/v1/admin/catalog/templates",
                                  json=bad, headers=admin_header)
        assert resp.status_code == 400


class TestUpdateTemplateStatus:
    def test_deprecate_template(self, admin_client, admin_header):
        # Create v1 and v2
        admin_client.post("/api/v1/admin/catalog/templates",
                           json=_valid_template(version="1.0.0"), headers=admin_header)
        resp2 = admin_client.post("/api/v1/admin/catalog/templates",
                                   json=_valid_template(version="2.0.0"), headers=admin_header)
        v2_id = resp2.get_json()["id"]

        # Get v1 id
        resp1 = admin_client.get("/api/v1/catalog/templates/vm-linux?version=1.0.0",
                                  headers=admin_header)
        v1_id = resp1.get_json()["id"]

        # Deprecate v1, pointing to v2
        resp = admin_client.patch(f"/api/v1/admin/catalog/templates/{v1_id}/status",
                                   json={"status": "deprecated", "deprecated_by": v2_id},
                                   headers=admin_header)
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "deprecated"

    def test_invalid_transition(self, admin_client, admin_header):
        resp = admin_client.post("/api/v1/admin/catalog/templates",
                                  json=_valid_template(), headers=admin_header)
        tid = resp.get_json()["id"]

        # Disable it
        admin_client.patch(f"/api/v1/admin/catalog/templates/{tid}/status",
                            json={"status": "disabled"}, headers=admin_header)

        # Try to deprecate disabled template
        resp = admin_client.patch(f"/api/v1/admin/catalog/templates/{tid}/status",
                                   json={"status": "deprecated"}, headers=admin_header)
        assert resp.status_code == 409

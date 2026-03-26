# tests/integration/test_context_restrictions_api.py
import pytest
from app import create_app
from app.data.db.session import get_engine, get_session_factory, Base


@pytest.fixture
def admin_app():
    app = create_app({
        "AUTH_MODE": "stub", "ENV": "development", "TESTING": "True",
        "DATABASE_URL": "postgresql://mpp:mpp@localhost:5432/mpp_test",
        "CMDB_MODE": "stub",
    })
    engine = get_engine(app.config["DATABASE_URL"])
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield app, engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def client(admin_app):
    app, _ = admin_app
    return app.test_client()


@pytest.fixture
def admin_header(client):
    resp = client.post("/api/v1/auth/login", json={"username": "test-admin"})
    return {"Authorization": f"Bearer {resp.get_json()['token']}"}


@pytest.fixture
def requester_header(client):
    resp = client.post("/api/v1/auth/login", json={"username": "test-requester"})
    return {"Authorization": f"Bearer {resp.get_json()['token']}"}


def _valid_restriction(**overrides):
    restriction = {
        "name": "Max CPU for medium zone",
        "template_slug": "vm-linux",
        "parameter_key": "cpu_cores",
        "restriction_type": "override_max",
        "conditions": {"security_zone_id": "sz-medium"},
        "effect": {"max": 8},
        "priority": 5,
    }
    restriction.update(overrides)
    return restriction


class TestCreateRestriction:
    def test_create_restriction_success(self, client, admin_header):
        resp = client.post("/api/v1/admin/context/restrictions",
                           json=_valid_restriction(), headers=admin_header)
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["name"] == "Max CPU for medium zone"
        assert data["template_slug"] == "vm-linux"
        assert data["parameter_key"] == "cpu_cores"
        assert data["restriction_type"] == "override_max"
        assert data["conditions"] == {"security_zone_id": "sz-medium"}
        assert data["effect"] == {"max": 8}
        assert data["priority"] == 5
        assert data["is_active"] is True
        assert "id" in data

    def test_create_restriction_requires_admin(self, client, requester_header):
        resp = client.post("/api/v1/admin/context/restrictions",
                           json=_valid_restriction(), headers=requester_header)
        assert resp.status_code == 403


class TestListRestrictions:
    def test_list_restrictions(self, client, admin_header):
        client.post("/api/v1/admin/context/restrictions",
                     json=_valid_restriction(), headers=admin_header)
        client.post("/api/v1/admin/context/restrictions",
                     json=_valid_restriction(name="Disk filter",
                                             parameter_key="disk_type",
                                             restriction_type="filter_options"),
                     headers=admin_header)

        resp = client.get("/api/v1/admin/context/restrictions",
                          headers=admin_header)
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 2

    def test_list_restrictions_filter_by_template(self, client, admin_header):
        client.post("/api/v1/admin/context/restrictions",
                     json=_valid_restriction(), headers=admin_header)
        client.post("/api/v1/admin/context/restrictions",
                     json=_valid_restriction(name="Win restriction",
                                             template_slug="vm-windows"),
                     headers=admin_header)

        resp = client.get("/api/v1/admin/context/restrictions?template_slug=vm-linux",
                          headers=admin_header)
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 1


class TestDeleteRestriction:
    def test_delete_restriction(self, client, admin_header):
        resp = client.post("/api/v1/admin/context/restrictions",
                           json=_valid_restriction(), headers=admin_header)
        rid = resp.get_json()["id"]

        resp = client.delete(f"/api/v1/admin/context/restrictions/{rid}",
                             headers=admin_header)
        assert resp.status_code == 204

        resp = client.get("/api/v1/admin/context/restrictions",
                          headers=admin_header)
        assert len(resp.get_json()) == 0

    def test_delete_nonexistent_returns_404(self, client, admin_header):
        resp = client.delete("/api/v1/admin/context/restrictions/nonexistent",
                             headers=admin_header)
        assert resp.status_code == 404


class TestResolveParameters:
    def test_resolve_with_restriction(self, client, admin_header):
        client.post("/api/v1/admin/context/restrictions",
                     json=_valid_restriction(
                         restriction_type="override_max",
                         conditions={"security_zone_id": "sz-medium"},
                         effect={"max": 8},
                     ), headers=admin_header)

        resp = client.post("/api/v1/context/resolve-parameters",
                           json={
                               "template_slug": "vm-linux",
                               "parameter_key": "cpu_cores",
                               "context": {"security_zone_id": "sz-medium"},
                           }, headers=admin_header)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["parameter_key"] == "cpu_cores"
        assert len(data["restrictions"]) == 1
        assert data["effective_constraints"]["max"] == 8

    def test_resolve_no_matching_restrictions(self, client, admin_header):
        resp = client.post("/api/v1/context/resolve-parameters",
                           json={
                               "template_slug": "vm-linux",
                               "parameter_key": "cpu_cores",
                               "context": {"security_zone_id": "sz-high"},
                           }, headers=admin_header)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["parameter_key"] == "cpu_cores"
        assert len(data["restrictions"]) == 0
        assert data["effective_constraints"] == {}

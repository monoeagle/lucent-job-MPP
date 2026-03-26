# tests/integration/test_availability_rules_api.py
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


def _valid_rule(**overrides):
    rule = {
        "name": "Berlin Allow Rule",
        "template_slug": "vm-linux",
        "rule_type": "allow",
        "conditions": {"location_id": "loc-berlin"},
        "priority": 10,
    }
    rule.update(overrides)
    return rule


class TestCreateAvailabilityRule:
    def test_create_rule_success(self, client, admin_header):
        resp = client.post("/api/v1/admin/context/availability-rules",
                           json=_valid_rule(), headers=admin_header)
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["name"] == "Berlin Allow Rule"
        assert data["template_slug"] == "vm-linux"
        assert data["rule_type"] == "allow"
        assert data["conditions"] == {"location_id": "loc-berlin"}
        assert data["priority"] == 10
        assert data["is_active"] is True
        assert "id" in data

    def test_create_rule_requires_admin(self, client, requester_header):
        resp = client.post("/api/v1/admin/context/availability-rules",
                           json=_valid_rule(), headers=requester_header)
        assert resp.status_code == 403


class TestListAvailabilityRules:
    def test_list_rules(self, client, admin_header):
        client.post("/api/v1/admin/context/availability-rules",
                     json=_valid_rule(), headers=admin_header)
        client.post("/api/v1/admin/context/availability-rules",
                     json=_valid_rule(name="Hamburg Deny", rule_type="deny",
                                      conditions={"location_id": "loc-hamburg"}),
                     headers=admin_header)

        resp = client.get("/api/v1/admin/context/availability-rules",
                          headers=admin_header)
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 2

    def test_list_rules_filter_by_template(self, client, admin_header):
        client.post("/api/v1/admin/context/availability-rules",
                     json=_valid_rule(), headers=admin_header)
        client.post("/api/v1/admin/context/availability-rules",
                     json=_valid_rule(name="Win Rule", template_slug="vm-windows"),
                     headers=admin_header)

        resp = client.get("/api/v1/admin/context/availability-rules?template_slug=vm-linux",
                          headers=admin_header)
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 1
        assert data[0]["template_slug"] == "vm-linux"


class TestUpdateAvailabilityRule:
    def test_update_rule(self, client, admin_header):
        resp = client.post("/api/v1/admin/context/availability-rules",
                           json=_valid_rule(), headers=admin_header)
        rule_id = resp.get_json()["id"]

        resp = client.patch(f"/api/v1/admin/context/availability-rules/{rule_id}",
                            json={"name": "Updated Name", "is_active": False},
                            headers=admin_header)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["name"] == "Updated Name"
        assert data["is_active"] is False

    def test_update_nonexistent_returns_404(self, client, admin_header):
        resp = client.patch("/api/v1/admin/context/availability-rules/nonexistent",
                            json={"name": "X"}, headers=admin_header)
        assert resp.status_code == 404


class TestDeleteAvailabilityRule:
    def test_delete_rule(self, client, admin_header):
        resp = client.post("/api/v1/admin/context/availability-rules",
                           json=_valid_rule(), headers=admin_header)
        rule_id = resp.get_json()["id"]

        resp = client.delete(f"/api/v1/admin/context/availability-rules/{rule_id}",
                             headers=admin_header)
        assert resp.status_code == 204

        resp = client.get("/api/v1/admin/context/availability-rules",
                          headers=admin_header)
        assert len(resp.get_json()) == 0

    def test_delete_nonexistent_returns_404(self, client, admin_header):
        resp = client.delete("/api/v1/admin/context/availability-rules/nonexistent",
                             headers=admin_header)
        assert resp.status_code == 404


class TestCheckAvailability:
    def test_check_availability_allowed(self, client, admin_header):
        client.post("/api/v1/admin/context/availability-rules",
                     json=_valid_rule(rule_type="allow",
                                      conditions={"location_id": "loc-berlin"}),
                     headers=admin_header)

        resp = client.post("/api/v1/context/check-availability",
                           json={"template_slug": "vm-linux",
                                 "context": {"location_id": "loc-berlin"}},
                           headers=admin_header)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["available"] is True
        assert data["matching_rule"] is not None

    def test_check_availability_denied(self, client, admin_header):
        client.post("/api/v1/admin/context/availability-rules",
                     json=_valid_rule(rule_type="deny",
                                      conditions={"location_id": "loc-berlin"}),
                     headers=admin_header)

        resp = client.post("/api/v1/context/check-availability",
                           json={"template_slug": "vm-linux",
                                 "context": {"location_id": "loc-berlin"}},
                           headers=admin_header)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["available"] is False

    def test_check_availability_no_rules(self, client, admin_header):
        resp = client.post("/api/v1/context/check-availability",
                           json={"template_slug": "vm-linux",
                                 "context": {"location_id": "loc-berlin"}},
                           headers=admin_header)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["available"] is True
        assert data["matching_rule"] is None

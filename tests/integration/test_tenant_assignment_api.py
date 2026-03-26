# tests/integration/test_tenant_assignment_api.py
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


class TestAssignTenant:
    def test_assign_tenant_success(self, client, admin_header):
        resp = client.post("/api/v1/admin/context/tenant-assignments",
                           json={"user_id": "user-alice", "tenant_id": "ten-corp"},
                           headers=admin_header)
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["user_id"] == "user-alice"
        assert data["tenant_id"] == "ten-corp"
        assert "id" in data

    def test_assign_duplicate_returns_409(self, client, admin_header):
        client.post("/api/v1/admin/context/tenant-assignments",
                     json={"user_id": "user-alice", "tenant_id": "ten-corp"},
                     headers=admin_header)
        resp = client.post("/api/v1/admin/context/tenant-assignments",
                           json={"user_id": "user-alice", "tenant_id": "ten-corp"},
                           headers=admin_header)
        assert resp.status_code == 409

    def test_assign_requires_admin(self, client, requester_header):
        resp = client.post("/api/v1/admin/context/tenant-assignments",
                           json={"user_id": "user-alice", "tenant_id": "ten-corp"},
                           headers=requester_header)
        assert resp.status_code == 403


class TestListAssignments:
    def test_list_all_assignments(self, client, admin_header):
        client.post("/api/v1/admin/context/tenant-assignments",
                     json={"user_id": "user-alice", "tenant_id": "ten-corp"},
                     headers=admin_header)
        client.post("/api/v1/admin/context/tenant-assignments",
                     json={"user_id": "user-bob", "tenant_id": "ten-corp"},
                     headers=admin_header)

        resp = client.get("/api/v1/admin/context/tenant-assignments",
                          headers=admin_header)
        assert resp.status_code == 200
        assert len(resp.get_json()) == 2

    def test_list_filter_by_user(self, client, admin_header):
        client.post("/api/v1/admin/context/tenant-assignments",
                     json={"user_id": "user-alice", "tenant_id": "ten-corp"},
                     headers=admin_header)
        client.post("/api/v1/admin/context/tenant-assignments",
                     json={"user_id": "user-bob", "tenant_id": "ten-corp"},
                     headers=admin_header)

        resp = client.get("/api/v1/admin/context/tenant-assignments?user_id=user-alice",
                          headers=admin_header)
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 1
        assert data[0]["user_id"] == "user-alice"


class TestDeleteAssignment:
    def test_delete_assignment(self, client, admin_header):
        resp = client.post("/api/v1/admin/context/tenant-assignments",
                           json={"user_id": "user-alice", "tenant_id": "ten-corp"},
                           headers=admin_header)
        aid = resp.get_json()["id"]

        resp = client.delete(f"/api/v1/admin/context/tenant-assignments/{aid}",
                             headers=admin_header)
        assert resp.status_code == 204

        resp = client.get("/api/v1/admin/context/tenant-assignments",
                          headers=admin_header)
        assert len(resp.get_json()) == 0

    def test_delete_nonexistent_returns_404(self, client, admin_header):
        resp = client.delete("/api/v1/admin/context/tenant-assignments/nonexistent",
                             headers=admin_header)
        assert resp.status_code == 404


class TestTenantAssignmentContextIntegration:
    def test_context_resolve_respects_tenant_assignment(self, client, admin_header):
        """When user has tenant assignments, they can only use assigned tenants."""
        # Assign test-admin only to ten-corp
        client.post("/api/v1/admin/context/tenant-assignments",
                     json={"user_id": "test-admin", "tenant_id": "ten-corp"},
                     headers=admin_header)

        # Resolve with assigned tenant should work
        resp = client.post("/api/v1/context/resolve",
                           json={
                               "location_id": "loc-berlin",
                               "tenant_id": "ten-corp",
                               "security_zone_id": "sz-medium",
                           }, headers=admin_header)
        assert resp.status_code == 200

    def test_context_resolve_rejects_unassigned_tenant(self, client, admin_header):
        """When user has tenant assignments, unassigned tenants are rejected."""
        # Assign test-admin only to ten-corp
        client.post("/api/v1/admin/context/tenant-assignments",
                     json={"user_id": "test-admin", "tenant_id": "ten-corp"},
                     headers=admin_header)

        # Resolve with unassigned tenant should fail
        resp = client.post("/api/v1/context/resolve",
                           json={
                               "location_id": "loc-berlin",
                               "tenant_id": "ten-startup",
                               "security_zone_id": "sz-medium",
                           }, headers=admin_header)
        assert resp.status_code == 400
        data = resp.get_json()
        assert any(v["field"] == "tenant_id" for v in data["violations"])

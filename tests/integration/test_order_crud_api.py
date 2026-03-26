# tests/integration/test_order_crud_api.py
import pytest
from app.data.db.session import get_engine, get_session_factory, Base
from app.data.repositories.order_repository import OrderRepository


@pytest.fixture
def db_session(app):
    engine = get_engine(app.config["DATABASE_URL"])
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Session = get_session_factory(engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def seed_order(db_session):
    """Create a draft order owned by test-requester."""
    repo = OrderRepository(db_session)
    order = repo.create_order("test-requester", "My Draft Order", "Need it", "2026-06-01")
    return order


@pytest.fixture
def seed_other_user_order(db_session):
    """Create a draft order owned by another user."""
    repo = OrderRepository(db_session)
    return repo.create_order("other-user", "Other Order", "Other reason")


@pytest.fixture
def seed_submitted_order(db_session):
    """Create a submitted order owned by test-requester."""
    repo = OrderRepository(db_session)
    order = repo.create_order("test-requester", "Submitted Order", "Reason")
    repo.update_order_status(order.id, "validated")
    repo.update_order_status(order.id, "submitted")
    return order


class TestCreateOrder:
    def test_create_order_returns_201(self, client, db_session, requester_headers):
        resp = client.post("/api/v1/orders", headers=requester_headers, json={
            "title": "New Server Setup",
            "business_reason": "Project X needs infra",
            "desired_date": "2026-07-01",
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["id"] is not None
        assert data["title"] == "New Server Setup"
        assert data["business_reason"] == "Project X needs infra"
        assert data["desired_date"] == "2026-07-01"
        assert data["status"] == "draft"
        assert data["requester_id"] == "test-requester"
        assert "order_number" in data
        assert "created_at" in data
        assert "items" in data

    def test_create_order_validation_error(self, client, db_session, requester_headers):
        resp = client.post("/api/v1/orders", headers=requester_headers, json={
            "title": "AB",  # too short
        })
        assert resp.status_code == 400

    def test_create_order_unauthenticated(self, client, db_session):
        resp = client.post("/api/v1/orders", json={"title": "Test"})
        assert resp.status_code == 401


class TestGetOrder:
    def test_get_order_returns_200(self, client, db_session, seed_order, requester_headers):
        resp = client.get(f"/api/v1/orders/{seed_order.id}", headers=requester_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["id"] == seed_order.id
        assert data["title"] == "My Draft Order"
        assert isinstance(data["items"], list)

    def test_get_nonexistent_order_returns_404(self, client, db_session, requester_headers):
        resp = client.get("/api/v1/orders/nonexistent-id", headers=requester_headers)
        assert resp.status_code == 404

    def test_get_other_users_order_returns_403(self, client, db_session, seed_other_user_order, requester_headers):
        resp = client.get(f"/api/v1/orders/{seed_other_user_order.id}", headers=requester_headers)
        assert resp.status_code == 403

    def test_admin_can_get_any_order(self, client, db_session, seed_other_user_order, admin_headers):
        resp = client.get(f"/api/v1/orders/{seed_other_user_order.id}", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.get_json()["id"] == seed_other_user_order.id


class TestListOrders:
    def test_list_own_orders(self, client, db_session, seed_order, seed_other_user_order, requester_headers):
        resp = client.get("/api/v1/orders", headers=requester_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "items" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        # requester should only see own orders
        for item in data["items"]:
            assert item["requester_id"] == "test-requester"

    def test_list_with_status_filter(self, client, db_session, seed_order, seed_submitted_order, requester_headers):
        resp = client.get("/api/v1/orders?status=draft", headers=requester_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        for item in data["items"]:
            assert item["status"] == "draft"

    def test_admin_sees_all_orders(self, client, db_session, seed_order, seed_other_user_order, admin_headers):
        resp = client.get("/api/v1/orders", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] >= 2


class TestUpdateOrder:
    def test_update_title(self, client, db_session, seed_order, requester_headers):
        resp = client.patch(f"/api/v1/orders/{seed_order.id}", headers=requester_headers, json={
            "title": "Updated Title",
        })
        assert resp.status_code == 200
        assert resp.get_json()["title"] == "Updated Title"

    def test_update_non_draft_returns_409(self, client, db_session, seed_submitted_order, requester_headers):
        resp = client.patch(f"/api/v1/orders/{seed_submitted_order.id}", headers=requester_headers, json={
            "title": "New Title",
        })
        assert resp.status_code == 409


class TestDeleteOrder:
    def test_delete_draft_returns_204(self, client, db_session, seed_order, requester_headers):
        resp = client.delete(f"/api/v1/orders/{seed_order.id}", headers=requester_headers)
        assert resp.status_code == 204

    def test_delete_non_draft_returns_409(self, client, db_session, seed_submitted_order, requester_headers):
        resp = client.delete(f"/api/v1/orders/{seed_submitted_order.id}", headers=requester_headers)
        assert resp.status_code == 409


class TestUnauthenticated:
    def test_all_endpoints_require_auth(self, client, db_session):
        assert client.get("/api/v1/orders").status_code == 401
        assert client.get("/api/v1/orders/some-id").status_code == 401
        assert client.patch("/api/v1/orders/some-id", json={}).status_code == 401
        assert client.delete("/api/v1/orders/some-id").status_code == 401

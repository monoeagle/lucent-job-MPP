# tests/integration/test_dashboard_api.py
import pytest
from app.data.db.session import get_engine, get_session_factory, Base
from app.data.repositories.order_repository import OrderRepository
from app.data.repositories.template_repository import TemplateRepository


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
def seed_data(db_session):
    """Create 1 template + 2 orders with items (both reference the same template)."""
    tmpl_repo = TemplateRepository(db_session)
    tmpl_repo.create({
        "slug": "vm-linux",
        "version": "1.0.0",
        "type": "vm",
        "display_name": "Linux VM",
        "category": "Compute",
        "tofu_module_source": "git::https://gitlab.internal/tofu/vm.git",
        "parameters": [],
    })

    order_repo = OrderRepository(db_session)

    draft = order_repo.create_order("test-requester", "Draft Order")

    submitted = order_repo.create_order("test-requester", "Submitted Order")
    order_repo.add_item(submitted.id, "vm-linux", "1.0.0", "Linux VM", {})
    order_repo.add_item(submitted.id, "vm-linux", "1.0.0", "Linux VM 2", {})
    order_repo.update_order_status(submitted.id, "validated")
    order_repo.update_order_status(submitted.id, "submitted")

    return {"draft": draft, "submitted": submitted}


class TestDashboardStats:
    def test_stats_unauthenticated_returns_401(self, client, db_session):
        resp = client.get("/api/v1/dashboard/stats")
        assert resp.status_code == 401

    def test_stats_returns_200(self, client, db_session, seed_data, requester_headers):
        resp = client.get("/api/v1/dashboard/stats", headers=requester_headers)
        assert resp.status_code == 200
        body = resp.get_json()
        assert "orders_by_status" in body
        assert "orders_by_month" in body
        assert "total_templates" in body
        assert "active_resources" in body
        assert "pending_approvals" in body
        assert "popular_templates" in body

    def test_stats_counts_orders_by_status(self, client, db_session, seed_data, requester_headers):
        resp = client.get("/api/v1/dashboard/stats", headers=requester_headers)
        assert resp.status_code == 200
        body = resp.get_json()
        orders_by_status = body["orders_by_status"]
        assert orders_by_status.get("draft", 0) >= 1
        assert orders_by_status.get("submitted", 0) >= 1

    def test_stats_counts_templates(self, client, db_session, seed_data, requester_headers):
        resp = client.get("/api/v1/dashboard/stats", headers=requester_headers)
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["total_templates"] >= 1

    def test_stats_popular_templates(self, client, db_session, seed_data, requester_headers):
        resp = client.get("/api/v1/dashboard/stats", headers=requester_headers)
        assert resp.status_code == 200
        body = resp.get_json()
        popular = body["popular_templates"]
        assert len(popular) >= 1
        assert popular[0]["order_count"] >= 2

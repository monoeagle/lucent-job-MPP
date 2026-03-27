# tests/integration/test_admin_dashboard_api.py
import pytest
from app.data.db.session import get_engine, get_session_factory, Base
from app.data.repositories.order_repository import OrderRepository
from app.data.repositories.approval_repository import ApprovalRepository
from app.data.repositories.template_repository import TemplateRepository
from datetime import datetime, timedelta, timezone


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
def seed_dashboard_data(db_session):
    """Create orders in various statuses + an approval request."""
    order_repo = OrderRepository(db_session)

    # Draft orders
    order_repo.create_order("user-a", "Draft 1")
    order_repo.create_order("user-b", "Draft 2")

    # Submitted order
    o3 = order_repo.create_order("user-a", "Submitted Order")
    order_repo.update_order_status(o3.id, "validated")
    order_repo.update_order_status(o3.id, "submitted")

    # Done order with provisioned item
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
    o4 = order_repo.create_order("user-c", "Done Order")
    item = order_repo.add_item(o4.id, "vm-linux", "1.0.0", "Linux VM", {})
    order_repo.update_order_status(o4.id, "validated")
    order_repo.update_order_status(o4.id, "submitted")
    order_repo.update_order_status(o4.id, "done")
    item.provisioning_status = "done"
    db_session.commit()

    # Pending approval order
    o5 = order_repo.create_order("user-d", "Pending Approval Order")
    order_repo.update_order_status(o5.id, "validated")
    order_repo.update_order_status(o5.id, "submitted")
    order_repo.update_order_status(o5.id, "pending_approval")

    approval_repo = ApprovalRepository(db_session)
    approval_repo.create_request(
        order_id=o5.id,
        approval_rule_ids=["rule-1"],
        deadline_at=datetime.now(timezone.utc) + timedelta(hours=48),
    )

    return {
        "draft_count": 2,
        "submitted_count": 1,
        "done_count": 1,
        "pending_approval_count": 1,
        "total_orders": 5,
    }


class TestAdminDashboard:
    def test_dashboard_returns_order_counts(
        self, client, db_session, seed_dashboard_data, admin_headers,
    ):
        resp = client.get("/api/v1/admin/dashboard", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.get_json()

        counts = data["order_counts"]
        assert counts["draft"] == 2
        assert counts["submitted"] == 1
        assert counts["done"] == 1
        assert counts["pending_approval"] == 1
        assert counts["validated"] == 0
        assert counts["provisioning"] == 0
        assert counts["failed"] == 0

    def test_dashboard_has_pending_approvals(
        self, client, db_session, seed_dashboard_data, admin_headers,
    ):
        resp = client.get("/api/v1/admin/dashboard", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["pending_approvals"] == 1

    def test_dashboard_has_active_resources(
        self, client, db_session, seed_dashboard_data, admin_headers,
    ):
        resp = client.get("/api/v1/admin/dashboard", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["active_resources"] == 1

    def test_dashboard_has_recent_orders(
        self, client, db_session, seed_dashboard_data, admin_headers,
    ):
        resp = client.get("/api/v1/admin/dashboard", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["recent_orders"]) > 0
        order = data["recent_orders"][0]
        assert "order_id" in order
        assert "order_number" in order
        assert "title" in order
        assert "status" in order
        assert "created_at" in order

    def test_dashboard_has_system_health(
        self, client, db_session, seed_dashboard_data, admin_headers,
    ):
        resp = client.get("/api/v1/admin/dashboard", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "system_health" in data
        assert data["system_health"]["database"] == "ok"

    def test_dashboard_admin_only(
        self, client, db_session, requester_headers,
    ):
        resp = client.get("/api/v1/admin/dashboard", headers=requester_headers)
        assert resp.status_code == 403

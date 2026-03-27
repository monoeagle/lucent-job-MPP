# tests/integration/test_resources_api.py
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
def seed_done_order(db_session):
    """Create a completed order with a provisioned item."""
    tmpl_repo = TemplateRepository(db_session)
    tmpl_repo.create({
        "slug": "vm-linux",
        "version": "1.0.0",
        "type": "vm",
        "display_name": "Linux VM",
        "category": "Compute",
        "tofu_module_source": "git::https://gitlab.internal/tofu/vm.git",
        "parameters": [
            {
                "key": "cpu_cores", "label": "CPU", "type": "integer",
                "required": True, "tofu_variable_name": "cpu_cores",
                "display_order": 1, "constraints": {"min": 1, "max": 64},
            },
        ],
    })

    order_repo = OrderRepository(db_session)
    order = order_repo.create_order(
        "test-requester", "Provisioned Order", "Need VMs", "2026-06-01",
    )
    item = order_repo.add_item(
        order.id, "vm-linux", "1.0.0", "Linux VM", {"cpu_cores": 4},
    )
    order_repo.update_order_status(order.id, "validated")
    order_repo.update_order_status(order.id, "submitted")
    order_repo.update_order_status(order.id, "done")

    # Mark item as provisioned
    item.provisioning_status = "done"
    db_session.commit()

    return order, item


class TestListResources:
    def test_list_resources_returns_provisioned_items(
        self, client, db_session, seed_done_order, requester_headers,
    ):
        order, item = seed_done_order
        resp = client.get("/api/v1/resources", headers=requester_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["items"]) == 1
        resource = data["items"][0]
        assert resource["item_id"] == item.id
        assert resource["template_slug"] == "vm-linux"
        assert resource["template_version"] == "1.0.0"
        assert resource["display_name"] == "Linux VM"
        assert resource["parameters"] == {"cpu_cores": 4}
        assert resource["order_id"] == order.id
        assert resource["order_number"] == order.order_number
        assert "provisioned_at" in resource

    def test_list_resources_empty_when_no_done_orders(
        self, client, db_session, requester_headers,
    ):
        resp = client.get("/api/v1/resources", headers=requester_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["items"] == []

    def test_list_resources_filter_by_service_type(
        self, client, db_session, seed_done_order, requester_headers,
    ):
        resp = client.get(
            "/api/v1/resources?service_type=vm", headers=requester_headers,
        )
        assert resp.status_code == 200
        assert len(resp.get_json()["items"]) == 1

        resp = client.get(
            "/api/v1/resources?service_type=storage", headers=requester_headers,
        )
        assert resp.status_code == 200
        assert len(resp.get_json()["items"]) == 0

    def test_list_resources_admin_sees_all(
        self, client, db_session, seed_done_order, admin_headers,
    ):
        resp = client.get("/api/v1/resources", headers=admin_headers)
        assert resp.status_code == 200
        assert len(resp.get_json()["items"]) == 1

    def test_list_resources_unauthenticated_returns_401(self, client, db_session):
        resp = client.get("/api/v1/resources")
        assert resp.status_code == 401


class TestResourceDetail:
    def test_get_resource_detail(
        self, client, db_session, seed_done_order, requester_headers,
    ):
        order, item = seed_done_order
        resp = client.get(
            f"/api/v1/resources/{item.id}", headers=requester_headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["item_id"] == item.id
        assert data["template_slug"] == "vm-linux"
        assert data["order_id"] == order.id
        assert data["order_number"] == order.order_number
        assert data["parameters"] == {"cpu_cores": 4}

    def test_get_resource_wrong_user_returns_403(
        self, client, db_session, seed_done_order, approver_headers,
    ):
        _, item = seed_done_order
        resp = client.get(
            f"/api/v1/resources/{item.id}", headers=approver_headers,
        )
        assert resp.status_code == 403

    def test_get_resource_not_found_returns_404(
        self, client, db_session, requester_headers,
    ):
        resp = client.get(
            "/api/v1/resources/nonexistent-id", headers=requester_headers,
        )
        assert resp.status_code == 404

# tests/integration/test_order_items_api.py
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
def seed_template(db_session):
    """Seed a valid active template into the DB."""
    repo = TemplateRepository(db_session)
    return repo.create({
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


@pytest.fixture
def seed_deprecated_template(db_session):
    """Seed a deprecated template."""
    repo = TemplateRepository(db_session)
    t = repo.create({
        "slug": "vm-old",
        "version": "0.9.0",
        "type": "vm",
        "display_name": "Old VM",
        "category": "Compute",
        "tofu_module_source": "git::https://gitlab.internal/tofu/vm-old.git",
        "parameters": [],
    })
    repo.update_status(t.id, "deprecated")
    return t


@pytest.fixture
def seed_disabled_template(db_session):
    """Seed a disabled template."""
    repo = TemplateRepository(db_session)
    t = repo.create({
        "slug": "vm-disabled",
        "version": "1.0.0",
        "type": "vm",
        "display_name": "Disabled VM",
        "category": "Compute",
        "tofu_module_source": "git::https://gitlab.internal/tofu/vm-disabled.git",
        "parameters": [],
    })
    repo.update_status(t.id, "disabled")
    return t


@pytest.fixture
def seed_order(db_session):
    """Create a draft order owned by test-requester."""
    repo = OrderRepository(db_session)
    return repo.create_order("test-requester", "My Draft Order", "Need it", "2026-06-01")


@pytest.fixture
def seed_submitted_order(db_session):
    """Create a submitted order."""
    repo = OrderRepository(db_session)
    order = repo.create_order("test-requester", "Submitted Order", "Reason")
    repo.update_order_status(order.id, "validated")
    repo.update_order_status(order.id, "submitted")
    return order


class TestAddItem:
    def test_add_item_to_draft_returns_201(
        self, client, db_session, seed_order, seed_template, requester_headers,
    ):
        resp = client.post(
            f"/api/v1/orders/{seed_order.id}/items",
            headers=requester_headers,
            json={
                "template_slug": "vm-linux",
                "template_version": "1.0.0",
                "parameters": {"cpu_cores": 4},
            },
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["item"]["template_slug"] == "vm-linux"
        assert data["item"]["template_version"] == "1.0.0"
        assert data["item"]["parameters"] == {"cpu_cores": 4}
        assert data["item"]["display_name"] == "Linux VM"
        assert data["item"]["position"] == 1
        assert data["item"]["validation_state"] == "unchecked"
        assert data.get("warning") is None

    def test_add_deprecated_template_returns_warning(
        self, client, db_session, seed_order, seed_deprecated_template, requester_headers,
    ):
        resp = client.post(
            f"/api/v1/orders/{seed_order.id}/items",
            headers=requester_headers,
            json={
                "template_slug": "vm-old",
                "template_version": "0.9.0",
                "parameters": {},
            },
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["warning"] is not None
        assert "deprecated" in data["warning"].lower()

    def test_add_item_nonexistent_template_returns_400(
        self, client, db_session, seed_order, requester_headers,
    ):
        resp = client.post(
            f"/api/v1/orders/{seed_order.id}/items",
            headers=requester_headers,
            json={
                "template_slug": "does-not-exist",
                "template_version": "1.0.0",
                "parameters": {},
            },
        )
        assert resp.status_code == 400

    def test_add_item_disabled_template_returns_400(
        self, client, db_session, seed_order, seed_disabled_template, requester_headers,
    ):
        resp = client.post(
            f"/api/v1/orders/{seed_order.id}/items",
            headers=requester_headers,
            json={
                "template_slug": "vm-disabled",
                "template_version": "1.0.0",
                "parameters": {},
            },
        )
        assert resp.status_code == 400

    def test_add_item_to_non_draft_returns_409(
        self, client, db_session, seed_submitted_order, seed_template, requester_headers,
    ):
        resp = client.post(
            f"/api/v1/orders/{seed_submitted_order.id}/items",
            headers=requester_headers,
            json={
                "template_slug": "vm-linux",
                "template_version": "1.0.0",
                "parameters": {},
            },
        )
        assert resp.status_code == 409

    def test_add_item_order_not_found_returns_404(
        self, client, db_session, seed_template, requester_headers,
    ):
        resp = client.post(
            "/api/v1/orders/nonexistent-id/items",
            headers=requester_headers,
            json={
                "template_slug": "vm-linux",
                "template_version": "1.0.0",
                "parameters": {},
            },
        )
        assert resp.status_code == 404


class TestUpdateItem:
    def test_update_item_parameters_returns_200(
        self, client, db_session, seed_order, seed_template, requester_headers,
    ):
        # First add an item
        add_resp = client.post(
            f"/api/v1/orders/{seed_order.id}/items",
            headers=requester_headers,
            json={
                "template_slug": "vm-linux",
                "template_version": "1.0.0",
                "parameters": {"cpu_cores": 4},
            },
        )
        item_id = add_resp.get_json()["item"]["id"]

        # Update parameters
        resp = client.patch(
            f"/api/v1/orders/{seed_order.id}/items/{item_id}",
            headers=requester_headers,
            json={"parameters": {"cpu_cores": 8}},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["item"]["parameters"] == {"cpu_cores": 8}
        assert data["item"]["validation_state"] == "unchecked"


class TestRemoveItem:
    def test_remove_item_returns_204(
        self, client, db_session, seed_order, seed_template, requester_headers,
    ):
        # Add an item first
        add_resp = client.post(
            f"/api/v1/orders/{seed_order.id}/items",
            headers=requester_headers,
            json={
                "template_slug": "vm-linux",
                "template_version": "1.0.0",
                "parameters": {"cpu_cores": 2},
            },
        )
        item_id = add_resp.get_json()["item"]["id"]

        resp = client.delete(
            f"/api/v1/orders/{seed_order.id}/items/{item_id}",
            headers=requester_headers,
        )
        assert resp.status_code == 204

    def test_remove_item_from_non_draft_returns_409(
        self, client, db_session, seed_submitted_order, requester_headers,
    ):
        resp = client.delete(
            f"/api/v1/orders/{seed_submitted_order.id}/items/fake-item-id",
            headers=requester_headers,
        )
        assert resp.status_code == 409


class TestReorderItems:
    def test_reorder_items_returns_200(
        self, client, db_session, seed_order, seed_template, requester_headers,
    ):
        # Add two items
        resp1 = client.post(
            f"/api/v1/orders/{seed_order.id}/items",
            headers=requester_headers,
            json={
                "template_slug": "vm-linux",
                "template_version": "1.0.0",
                "parameters": {"cpu_cores": 2},
            },
        )
        resp2 = client.post(
            f"/api/v1/orders/{seed_order.id}/items",
            headers=requester_headers,
            json={
                "template_slug": "vm-linux",
                "template_version": "1.0.0",
                "parameters": {"cpu_cores": 4},
            },
        )
        item1_id = resp1.get_json()["item"]["id"]
        item2_id = resp2.get_json()["item"]["id"]

        # Reorder: swap positions
        resp = client.put(
            f"/api/v1/orders/{seed_order.id}/items/positions",
            headers=requester_headers,
            json={
                "positions": [
                    {"item_id": item1_id, "position": 2},
                    {"item_id": item2_id, "position": 1},
                ],
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        items_by_id = {i["id"]: i for i in data["items"]}
        assert items_by_id[item1_id]["position"] == 2
        assert items_by_id[item2_id]["position"] == 1

    def test_reorder_non_draft_returns_409(
        self, client, db_session, seed_submitted_order, requester_headers,
    ):
        resp = client.put(
            f"/api/v1/orders/{seed_submitted_order.id}/items/positions",
            headers=requester_headers,
            json={"positions": []},
        )
        assert resp.status_code == 409

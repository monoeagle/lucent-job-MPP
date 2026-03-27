# tests/integration/test_order_quantity_api.py
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
def seed_template_with_per_instance(db_session):
    """Template with shared + per_instance parameters."""
    repo = TemplateRepository(db_session)
    return repo.create({
        "slug": "vm-cluster",
        "version": "1.0.0",
        "type": "vm",
        "display_name": "Cluster VM",
        "category": "Compute",
        "tofu_module_source": "git::https://gitlab.internal/tofu/vm-cluster.git",
        "parameters": [
            {
                "key": "cpu_cores", "label": "CPU", "type": "integer",
                "required": True, "tofu_variable_name": "cpu_cores",
                "display_order": 1, "constraints": {"min": 1, "max": 64},
            },
            {
                "key": "hostname", "label": "Hostname", "type": "string",
                "required": True, "tofu_variable_name": "hostname",
                "display_order": 2, "per_instance": True,
            },
        ],
    })


@pytest.fixture
def seed_template_no_per_instance(db_session):
    """Template without any per_instance parameters."""
    repo = TemplateRepository(db_session)
    return repo.create({
        "slug": "vm-simple",
        "version": "1.0.0",
        "type": "vm",
        "display_name": "Simple VM",
        "category": "Compute",
        "tofu_module_source": "git::https://gitlab.internal/tofu/vm-simple.git",
        "parameters": [
            {
                "key": "cpu_cores", "label": "CPU", "type": "integer",
                "required": True, "tofu_variable_name": "cpu_cores",
                "display_order": 1, "constraints": {"min": 1, "max": 64},
            },
        ],
    })


@pytest.fixture
def seed_order(db_session):
    repo = OrderRepository(db_session)
    return repo.create_order("test-requester", "Quantity Test", "Need VMs", "2026-06-01")


# ── Add Item with Quantity ───────────────────────────────────


class TestAddItemWithQuantity:
    def test_add_item_quantity_3_with_instance_params_returns_201(
        self, client, db_session, seed_order, seed_template_with_per_instance,
        requester_headers,
    ):
        resp = client.post(
            f"/api/v1/orders/{seed_order.id}/items",
            headers=requester_headers,
            json={
                "template_slug": "vm-cluster",
                "template_version": "1.0.0",
                "parameters": {"cpu_cores": 4},
                "quantity": 3,
                "instance_parameters": [
                    {"hostname": "web-01"},
                    {"hostname": "web-02"},
                    {"hostname": "web-03"},
                ],
            },
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["item"]["quantity"] == 3
        assert len(data["item"]["instance_parameters"]) == 3
        assert data["item"]["instance_parameters"][0]["hostname"] == "web-01"

    def test_add_item_quantity_1_default_backwards_compatible(
        self, client, db_session, seed_order, seed_template_no_per_instance,
        requester_headers,
    ):
        resp = client.post(
            f"/api/v1/orders/{seed_order.id}/items",
            headers=requester_headers,
            json={
                "template_slug": "vm-simple",
                "template_version": "1.0.0",
                "parameters": {"cpu_cores": 2},
            },
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["item"]["quantity"] == 1
        assert data["item"]["instance_parameters"] == []


# ── GET Order shows quantity ─────────────────────────────────


class TestGetOrderWithQuantity:
    def test_get_order_shows_item_quantity_and_instance_params(
        self, client, db_session, seed_order, seed_template_with_per_instance,
        requester_headers,
    ):
        client.post(
            f"/api/v1/orders/{seed_order.id}/items",
            headers=requester_headers,
            json={
                "template_slug": "vm-cluster",
                "template_version": "1.0.0",
                "parameters": {"cpu_cores": 4},
                "quantity": 2,
                "instance_parameters": [
                    {"hostname": "app-01"},
                    {"hostname": "app-02"},
                ],
            },
        )

        resp = client.get(
            f"/api/v1/orders/{seed_order.id}",
            headers=requester_headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        item = data["items"][0]
        assert item["quantity"] == 2
        assert len(item["instance_parameters"]) == 2


# ── Validate with Quantity ───────────────────────────────────


class TestValidateWithQuantity:
    def test_validate_quantity_item_all_valid(
        self, client, db_session, seed_order, seed_template_with_per_instance,
        requester_headers,
    ):
        client.post(
            f"/api/v1/orders/{seed_order.id}/items",
            headers=requester_headers,
            json={
                "template_slug": "vm-cluster",
                "template_version": "1.0.0",
                "parameters": {"cpu_cores": 4},
                "quantity": 2,
                "instance_parameters": [
                    {"hostname": "web-01"},
                    {"hostname": "web-02"},
                ],
            },
        )

        resp = client.post(
            f"/api/v1/orders/{seed_order.id}/validate",
            headers=requester_headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["all_valid"] is True


# ── Export with Quantity ─────────────────────────────────────


class TestExportWithQuantity:
    def test_export_quantity_3_produces_3_tofu_blocks(
        self, client, db_session, seed_order, seed_template_with_per_instance,
        requester_headers,
    ):
        # Add item with quantity=3
        client.post(
            f"/api/v1/orders/{seed_order.id}/items",
            headers=requester_headers,
            json={
                "template_slug": "vm-cluster",
                "template_version": "1.0.0",
                "parameters": {"cpu_cores": 8},
                "quantity": 3,
                "instance_parameters": [
                    {"hostname": "node-01"},
                    {"hostname": "node-02"},
                    {"hostname": "node-03"},
                ],
            },
        )

        # Validate and submit
        client.post(
            f"/api/v1/orders/{seed_order.id}/validate",
            headers=requester_headers,
        )
        client.post(
            f"/api/v1/orders/{seed_order.id}/submit",
            headers=requester_headers,
        )

        # Export
        resp = client.get(
            f"/api/v1/orders/{seed_order.id}/export/tofu",
            headers=requester_headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["items"]) == 3
        hostnames = [item["variables"]["hostname"] for item in data["items"]]
        assert hostnames == ["node-01", "node-02", "node-03"]
        # All share same cpu_cores
        for item in data["items"]:
            assert item["variables"]["cpu_cores"] == 8

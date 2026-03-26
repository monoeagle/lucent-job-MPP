# tests/integration/test_order_validation_api.py
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
    """Seed a valid active template with cpu_cores (min=1, max=64)."""
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


class TestValidateOrder:
    def test_validate_with_valid_params_returns_200(
        self, client, db_session, seed_order, seed_template, requester_headers,
    ):
        # Add an item with valid parameters
        client.post(
            f"/api/v1/orders/{seed_order.id}/items",
            headers=requester_headers,
            json={
                "template_slug": "vm-linux",
                "template_version": "1.0.0",
                "parameters": {"cpu_cores": 4},
            },
        )

        resp = client.post(
            f"/api/v1/orders/{seed_order.id}/validate",
            headers=requester_headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["order_id"] == seed_order.id
        assert data["order_status"] == "validated"
        assert data["all_valid"] is True
        assert len(data["item_results"]) == 1

        item_result = data["item_results"][0]
        assert item_result["template_slug"] == "vm-linux"
        assert item_result["template_version"] == "1.0.0"
        assert item_result["position"] == 1
        assert item_result["validation_state"] == "valid"
        assert item_result["violations"] == []

    def test_validate_with_invalid_params_returns_200(
        self, client, db_session, seed_order, seed_template, requester_headers,
    ):
        # Add an item with cpu_cores out of range (max=64)
        client.post(
            f"/api/v1/orders/{seed_order.id}/items",
            headers=requester_headers,
            json={
                "template_slug": "vm-linux",
                "template_version": "1.0.0",
                "parameters": {"cpu_cores": 128},
            },
        )

        resp = client.post(
            f"/api/v1/orders/{seed_order.id}/validate",
            headers=requester_headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["order_status"] == "draft"
        assert data["all_valid"] is False

        item_result = data["item_results"][0]
        assert item_result["validation_state"] == "invalid"
        assert len(item_result["violations"]) > 0

    def test_validate_empty_order_returns_409(
        self, client, db_session, seed_order, requester_headers,
    ):
        # No items added
        resp = client.post(
            f"/api/v1/orders/{seed_order.id}/validate",
            headers=requester_headers,
        )
        assert resp.status_code == 409

    def test_validate_submitted_order_returns_409(
        self, client, db_session, seed_submitted_order, requester_headers,
    ):
        resp = client.post(
            f"/api/v1/orders/{seed_submitted_order.id}/validate",
            headers=requester_headers,
        )
        assert resp.status_code == 409

    def test_validate_unauthenticated_returns_401(
        self, client, db_session, seed_order,
    ):
        resp = client.post(
            f"/api/v1/orders/{seed_order.id}/validate",
        )
        assert resp.status_code == 401

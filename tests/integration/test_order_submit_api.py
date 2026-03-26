# tests/integration/test_order_submit_api.py
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


def _create_validated_order(client, headers, seed_template):
    """Helper: create order, add item, validate → returns order_id."""
    resp = client.post(
        "/api/v1/orders",
        headers=headers,
        json={"title": "Submit Test Order", "business_reason": "We need this VM"},
    )
    order_id = resp.get_json()["id"]

    client.post(
        f"/api/v1/orders/{order_id}/items",
        headers=headers,
        json={
            "template_slug": "vm-linux",
            "template_version": "1.0.0",
            "parameters": {"cpu_cores": 4},
        },
    )

    client.post(f"/api/v1/orders/{order_id}/validate", headers=headers)
    return order_id


class TestSubmitOrder:
    def test_submit_validated_order_returns_200(
        self, client, db_session, seed_template, requester_headers,
    ):
        order_id = _create_validated_order(client, requester_headers, seed_template)

        resp = client.post(
            f"/api/v1/orders/{order_id}/submit",
            headers=requester_headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["order_id"] == order_id
        assert data["status"] == "submitted"
        assert data["item_count"] == 1
        assert data["submitted_at"] is not None
        assert "order_number" in data
        assert data["message"] == "Ihre Bestellung wurde erfolgreich eingereicht."

    def test_submit_draft_order_returns_409(
        self, client, db_session, seed_template, requester_headers,
    ):
        resp = client.post(
            "/api/v1/orders",
            headers=requester_headers,
            json={"title": "Draft Order", "business_reason": "Reason"},
        )
        order_id = resp.get_json()["id"]

        resp = client.post(
            f"/api/v1/orders/{order_id}/submit",
            headers=requester_headers,
        )
        assert resp.status_code == 409

    def test_submit_already_submitted_order_returns_409(
        self, client, db_session, seed_template, requester_headers,
    ):
        order_id = _create_validated_order(client, requester_headers, seed_template)
        client.post(f"/api/v1/orders/{order_id}/submit", headers=requester_headers)

        resp = client.post(
            f"/api/v1/orders/{order_id}/submit",
            headers=requester_headers,
        )
        assert resp.status_code == 409

    def test_submit_without_business_reason_returns_409(
        self, client, db_session, seed_template, requester_headers,
    ):
        # Create order without business_reason
        resp = client.post(
            "/api/v1/orders",
            headers=requester_headers,
            json={"title": "No Reason Order"},
        )
        order_id = resp.get_json()["id"]

        # Add item and force-validate via repo
        client.post(
            f"/api/v1/orders/{order_id}/items",
            headers=requester_headers,
            json={
                "template_slug": "vm-linux",
                "template_version": "1.0.0",
                "parameters": {"cpu_cores": 4},
            },
        )
        client.post(f"/api/v1/orders/{order_id}/validate", headers=requester_headers)

        resp = client.post(
            f"/api/v1/orders/{order_id}/submit",
            headers=requester_headers,
        )
        assert resp.status_code == 409

    def test_submit_unauthenticated_returns_401(
        self, client, db_session, seed_template, requester_headers,
    ):
        order_id = _create_validated_order(client, requester_headers, seed_template)
        resp = client.post(f"/api/v1/orders/{order_id}/submit")
        assert resp.status_code == 401


class TestOrderStatus:
    def test_get_status_after_submit_returns_200(
        self, client, db_session, seed_template, requester_headers,
    ):
        order_id = _create_validated_order(client, requester_headers, seed_template)
        client.post(f"/api/v1/orders/{order_id}/submit", headers=requester_headers)

        resp = client.get(
            f"/api/v1/orders/{order_id}/status",
            headers=requester_headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["order_id"] == order_id
        assert data["status"] == "submitted"
        assert "order_number" in data
        assert data["submitted_at"] is not None
        assert "updated_at" in data

        assert len(data["item_statuses"]) == 1
        item_status = data["item_statuses"][0]
        assert "item_id" in item_status
        assert item_status["position"] == 1
        assert item_status["template_slug"] == "vm-linux"
        assert item_status["provisioning_status"] == "not_started"
        assert item_status["job_id"] is None

    def test_get_status_unauthenticated_returns_401(
        self, client, db_session, seed_template, requester_headers,
    ):
        order_id = _create_validated_order(client, requester_headers, seed_template)
        resp = client.get(f"/api/v1/orders/{order_id}/status")
        assert resp.status_code == 401

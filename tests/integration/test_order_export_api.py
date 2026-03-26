# tests/integration/test_order_export_api.py
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


def _create_submitted_order(client, headers, seed_template):
    """Helper: create order, add item, validate, submit → returns (order_id, item_id)."""
    resp = client.post(
        "/api/v1/orders",
        headers=headers,
        json={"title": "Export Test Order", "business_reason": "Need a VM"},
    )
    order_id = resp.get_json()["id"]

    resp = client.post(
        f"/api/v1/orders/{order_id}/items",
        headers=headers,
        json={
            "template_slug": "vm-linux",
            "template_version": "1.0.0",
            "parameters": {"cpu_cores": 4},
        },
    )
    item_id = resp.get_json()["item"]["id"]

    client.post(f"/api/v1/orders/{order_id}/validate", headers=headers)
    client.post(f"/api/v1/orders/{order_id}/submit", headers=headers)
    return order_id, item_id


class TestExportOrderTofu:
    def test_export_submitted_order_returns_200(
        self, client, db_session, seed_template, requester_headers,
    ):
        order_id, _ = _create_submitted_order(client, requester_headers, seed_template)

        resp = client.get(
            f"/api/v1/orders/{order_id}/export/tofu",
            headers=requester_headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["order_id"] == order_id
        assert "order_number" in data
        assert "exported_at" in data
        assert data["readonly_notice"] is None

        assert len(data["items"]) == 1
        item = data["items"][0]
        assert "order_item_id" in item
        assert item["template_slug"] == "vm-linux"
        assert item["template_version"] == "1.0.0"
        assert item["position"] == 1
        assert item["variables"]["cpu_cores"] == 4
        assert item["error"] is None

    def test_export_draft_order_returns_409(
        self, client, db_session, seed_template, requester_headers,
    ):
        resp = client.post(
            "/api/v1/orders",
            headers=requester_headers,
            json={"title": "Draft Order", "business_reason": "Reason"},
        )
        order_id = resp.get_json()["id"]

        resp = client.get(
            f"/api/v1/orders/{order_id}/export/tofu",
            headers=requester_headers,
        )
        assert resp.status_code == 409

    def test_export_module_source_matches_template(
        self, client, db_session, seed_template, requester_headers,
    ):
        order_id, _ = _create_submitted_order(client, requester_headers, seed_template)

        resp = client.get(
            f"/api/v1/orders/{order_id}/export/tofu",
            headers=requester_headers,
        )
        data = resp.get_json()
        assert data["items"][0]["module_source"] == "git::https://gitlab.internal/tofu/vm.git"

    def test_export_unauthenticated_returns_401(
        self, client, db_session, seed_template, requester_headers,
    ):
        order_id, _ = _create_submitted_order(client, requester_headers, seed_template)
        resp = client.get(f"/api/v1/orders/{order_id}/export/tofu")
        assert resp.status_code == 401


class TestExportSingleItemTofu:
    def test_export_single_item_returns_200(
        self, client, db_session, seed_template, requester_headers,
    ):
        order_id, item_id = _create_submitted_order(client, requester_headers, seed_template)

        resp = client.get(
            f"/api/v1/orders/{order_id}/items/{item_id}/export/tofu",
            headers=requester_headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["order_item_id"] == item_id
        assert data["template_slug"] == "vm-linux"
        assert data["template_version"] == "1.0.0"
        assert data["position"] == 1
        assert data["module_source"] == "git::https://gitlab.internal/tofu/vm.git"
        assert data["variables"]["cpu_cores"] == 4
        assert data["error"] is None

    def test_export_single_item_draft_returns_409(
        self, client, db_session, seed_template, requester_headers,
    ):
        resp = client.post(
            "/api/v1/orders",
            headers=requester_headers,
            json={"title": "Draft Order", "business_reason": "Reason"},
        )
        order_id = resp.get_json()["id"]

        resp = client.post(
            f"/api/v1/orders/{order_id}/items",
            headers=requester_headers,
            json={
                "template_slug": "vm-linux",
                "template_version": "1.0.0",
                "parameters": {"cpu_cores": 4},
            },
        )
        item_id = resp.get_json()["item"]["id"]

        resp = client.get(
            f"/api/v1/orders/{order_id}/items/{item_id}/export/tofu",
            headers=requester_headers,
        )
        assert resp.status_code == 409

    def test_export_nonexistent_item_returns_404(
        self, client, db_session, seed_template, requester_headers,
    ):
        order_id, _ = _create_submitted_order(client, requester_headers, seed_template)

        resp = client.get(
            f"/api/v1/orders/{order_id}/items/nonexistent-id/export/tofu",
            headers=requester_headers,
        )
        assert resp.status_code == 404

    def test_export_single_item_unauthenticated_returns_401(
        self, client, db_session, seed_template, requester_headers,
    ):
        order_id, item_id = _create_submitted_order(client, requester_headers, seed_template)
        resp = client.get(f"/api/v1/orders/{order_id}/items/{item_id}/export/tofu")
        assert resp.status_code == 401

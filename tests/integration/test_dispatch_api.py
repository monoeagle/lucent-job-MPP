# tests/integration/test_dispatch_api.py
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
    """Create → add item → validate → submit → return order with item."""
    resp = client.post(
        "/api/v1/orders",
        headers=headers,
        json={"title": "Dispatch Test Order", "business_reason": "Testing dispatch"},
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


class TestManualDispatch:
    def test_manual_dispatch_returns_202(
        self, client, db_session, seed_template, requester_headers, admin_headers,
    ):
        order_id, item_id = _create_submitted_order(
            client, requester_headers, seed_template,
        )

        resp = client.post(
            f"/api/v1/admin/orders/{order_id}/items/{item_id}/dispatch",
            headers=admin_headers,
        )
        assert resp.status_code == 202

    def test_manual_dispatch_requires_admin(
        self, client, db_session, seed_template, requester_headers,
    ):
        order_id, item_id = _create_submitted_order(
            client, requester_headers, seed_template,
        )

        resp = client.post(
            f"/api/v1/admin/orders/{order_id}/items/{item_id}/dispatch",
            headers=requester_headers,
        )
        assert resp.status_code == 403

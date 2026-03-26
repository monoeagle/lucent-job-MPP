# tests/integration/test_order_context_integration.py
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


VALID_CONTEXT = {
    "location_id": "loc-berlin",
    "tenant_id": "ten-corp",
    "security_zone_id": "sz-medium",
    "network_id": None,
}


class TestCreateOrderWithContext:
    def test_create_order_with_context_returns_201(
        self, client, db_session, seed_template, requester_headers,
    ):
        resp = client.post("/api/v1/orders", headers=requester_headers, json={
            "title": "Order with context",
            "business_reason": "Testing context",
            "context": VALID_CONTEXT,
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["context"] is not None
        assert data["context"]["location_id"] == "loc-berlin"
        assert data["context"]["tenant_id"] == "ten-corp"
        assert data["context"]["security_zone_id"] == "sz-medium"

    def test_create_order_without_context_returns_201(
        self, client, db_session, seed_template, requester_headers,
    ):
        resp = client.post("/api/v1/orders", headers=requester_headers, json={
            "title": "Order without context",
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["context"] is None

    def test_get_order_includes_context(
        self, client, db_session, seed_template, requester_headers,
    ):
        # Create with context
        create_resp = client.post("/api/v1/orders", headers=requester_headers, json={
            "title": "Order for GET test",
            "context": VALID_CONTEXT,
        })
        order_id = create_resp.get_json()["id"]

        # GET should include context
        resp = client.get(f"/api/v1/orders/{order_id}", headers=requester_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["context"] is not None
        assert data["context"]["location_id"] == "loc-berlin"

    def test_create_order_with_invalid_context_returns_400(
        self, client, db_session, seed_template, requester_headers,
    ):
        resp = client.post("/api/v1/orders", headers=requester_headers, json={
            "title": "Order with bad context",
            "context": {
                "location_id": "loc-unknown",
                "tenant_id": "ten-corp",
                "security_zone_id": "sz-medium",
            },
        })
        assert resp.status_code == 400
        data = resp.get_json()
        assert "violations" in data or "message" in data

    def test_context_included_in_order_list(
        self, client, db_session, seed_template, requester_headers,
    ):
        # Create order with context
        client.post("/api/v1/orders", headers=requester_headers, json={
            "title": "Order for list test",
            "context": VALID_CONTEXT,
        })

        resp = client.get("/api/v1/orders", headers=requester_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["items"]) >= 1
        order = data["items"][0]
        assert "context" in order
        assert order["context"]["location_id"] == "loc-berlin"

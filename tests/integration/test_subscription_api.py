# tests/integration/test_subscription_api.py
import uuid
import pytest

from app.data.db.session import get_engine, get_session_factory, Base


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
def active_subscription(db_session):
    """Seed a template + order + order item + active subscription. Returns the subscription."""
    from app.data.db.models.service_template import ServiceTemplateModel
    from app.data.repositories.order_repository import OrderRepository
    from app.data.repositories.subscription_repository import SubscriptionRepository

    template = ServiceTemplateModel(
        id=str(uuid.uuid4()),
        slug="vm-linux",
        version="1.0.0",
        type="vm",
        display_name="Linux VM",
        category="compute",
        tofu_module_source="git::https://example.com/modules/vm-linux",
        parameters=[],
    )
    db_session.add(template)
    db_session.commit()

    order_repo = OrderRepository(db_session)
    order = order_repo.create_order(
        requester_id="test-requester",
        title="Subscription Test Order",
    )
    item = order_repo.add_item(
        order_id=order.id,
        template_slug="vm-linux",
        template_version="1.0.0",
        display_name="My Linux VM",
        parameters={"cpu": 2, "ram_gb": 8},
    )
    db_session.refresh(item)

    sub_repo = SubscriptionRepository(db_session)
    sub = sub_repo.create_from_order_item(item)
    # Activate so change/cancel operations work
    sub_repo.update_status(sub.id, "active")
    db_session.refresh(sub)
    return sub


class TestListSubscriptions:
    def test_list_returns_200(self, client, db_session, active_subscription, requester_headers):
        resp = client.get("/api/v1/subscriptions", headers=requester_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "items" in data
        assert data["total"] >= 1
        ids = [s["id"] for s in data["items"]]
        assert active_subscription.id in ids

    def test_list_unauthenticated_401(self, client, db_session):
        resp = client.get("/api/v1/subscriptions")
        assert resp.status_code == 401


class TestGetSubscription:
    def test_get_returns_200(self, client, db_session, active_subscription, requester_headers):
        resp = client.get(
            f"/api/v1/subscriptions/{active_subscription.id}",
            headers=requester_headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["id"] == active_subscription.id
        assert data["status"] == "active"
        assert data["template_slug"] == "vm-linux"

    def test_get_not_found_404(self, client, db_session, requester_headers):
        resp = client.get(
            f"/api/v1/subscriptions/{uuid.uuid4()}",
            headers=requester_headers,
        )
        assert resp.status_code == 404


class TestRequestChange:
    def test_change_returns_200(self, client, db_session, active_subscription, requester_headers):
        resp = client.post(
            f"/api/v1/subscriptions/{active_subscription.id}/change",
            headers=requester_headers,
            json={"parameters": {"cpu": 4, "ram_gb": 16}, "reason": "Need more resources"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "change_pending"
        assert data["pending_changes"] == {"cpu": 4, "ram_gb": 16}

    def test_change_not_active_409(self, client, db_session, active_subscription, requester_headers):
        # First request transitions to change_pending
        client.post(
            f"/api/v1/subscriptions/{active_subscription.id}/change",
            headers=requester_headers,
            json={"parameters": {"cpu": 4}},
        )
        # Second request on a non-active subscription should conflict
        resp = client.post(
            f"/api/v1/subscriptions/{active_subscription.id}/change",
            headers=requester_headers,
            json={"parameters": {"cpu": 8}},
        )
        assert resp.status_code == 409


class TestRequestCancel:
    def test_cancel_returns_200(self, client, db_session, active_subscription, requester_headers):
        resp = client.post(
            f"/api/v1/subscriptions/{active_subscription.id}/cancel",
            headers=requester_headers,
            json={"reason": "No longer needed"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "cancel_pending"

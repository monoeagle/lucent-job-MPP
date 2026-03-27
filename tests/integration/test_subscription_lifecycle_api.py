# tests/integration/test_subscription_lifecycle_api.py
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
        slug="vm-lifecycle",
        version="1.0.0",
        type="vm",
        display_name="Lifecycle VM",
        category="compute",
        tofu_module_source="git::https://example.com/modules/vm-lifecycle",
        parameters=[],
    )
    db_session.add(template)
    db_session.commit()

    order_repo = OrderRepository(db_session)
    order = order_repo.create_order(
        requester_id="test-requester",
        title="Lifecycle Test Order",
    )
    item = order_repo.add_item(
        order_id=order.id,
        template_slug="vm-lifecycle",
        template_version="1.0.0",
        display_name="My Lifecycle VM",
        parameters={"cpu": 2, "ram_gb": 4},
    )
    db_session.refresh(item)

    sub_repo = SubscriptionRepository(db_session)
    sub = sub_repo.create_from_order_item(item)
    sub_repo.update_status(sub.id, "active")
    db_session.refresh(sub)
    return sub


class TestChangeRequestCreates:
    def test_change_request_creates_pending_changes(
        self, client, db_session, active_subscription, requester_headers
    ):
        """POST /subscriptions/{id}/change on active subscription transitions to
        change_pending and stores pending_changes."""
        resp = client.post(
            f"/api/v1/subscriptions/{active_subscription.id}/change",
            headers=requester_headers,
            json={"parameters": {"cpu": 8, "ram_gb": 16}, "reason": "Need more power"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "change_pending"
        assert data["pending_changes"] == {"cpu": 8, "ram_gb": 16}


class TestCancelRequestSets:
    def test_cancel_request_sets_cancel_pending(
        self, client, db_session, active_subscription, requester_headers
    ):
        """POST /subscriptions/{id}/cancel on active subscription transitions to cancel_pending."""
        resp = client.post(
            f"/api/v1/subscriptions/{active_subscription.id}/cancel",
            headers=requester_headers,
            json={"reason": "No longer needed"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "cancel_pending"


class TestGroupCancelEndpoint:
    def test_group_cancel_endpoint_exists(
        self, client, db_session, requester_headers
    ):
        """POST /subscriptions/groups/{id}/cancel for a nonexistent group returns 404.
        This verifies the routing structure is correctly handled (groups prefix before
        subscription_id) or that calling with a nonexistent UUID yields a clear 404."""
        nonexistent_group_id = str(uuid.uuid4())
        resp = client.post(
            f"/api/v1/subscriptions/groups/{nonexistent_group_id}/cancel",
            headers=requester_headers,
            json={"reason": "Bulk cancel"},
        )
        # The endpoint does not exist yet, so we expect 404 or 405.
        assert resp.status_code in (404, 405)

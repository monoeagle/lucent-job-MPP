# tests/integration/test_post_submit_integration.py
import os
import pytest

from app import create_app
from app.data.db.session import get_engine, get_session_factory, Base
from app.data.repositories.template_repository import TemplateRepository


@pytest.fixture
def submit_app():
    app = create_app({
        "AUTH_MODE": "stub",
        "ENV": "development",
        "TESTING": "True",
        "DATABASE_URL": os.environ.get(
            "TEST_DATABASE_URL",
            "postgresql://mpp:mpp@localhost:5432/mpp_test",
        ),
    })
    engine = get_engine(app.config["DATABASE_URL"])
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield app
    Base.metadata.drop_all(engine)


@pytest.fixture
def submit_client(submit_app):
    return submit_app.test_client()


@pytest.fixture
def submit_session(submit_app):
    session = submit_app.session_factory()
    yield session
    session.close()


@pytest.fixture
def seeded_template(submit_session):
    repo = TemplateRepository(submit_session)
    return repo.create({
        "slug": "vm-notify",
        "version": "1.0.0",
        "type": "vm",
        "display_name": "Notify VM",
        "category": "Compute",
        "tofu_module_source": "git::https://gitlab.internal/tofu/vm.git",
        "parameters": [
            {
                "key": "cpu_cores",
                "label": "CPU",
                "type": "integer",
                "required": True,
                "tofu_variable_name": "cpu_cores",
                "display_order": 1,
                "constraints": {"min": 1, "max": 64},
            },
        ],
    })


def _auth_header(client, username="test-requester"):
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "stub-password"},
    )
    return {"Authorization": f"Bearer {resp.get_json()['token']}"}


def _create_and_submit_order(client, headers, template_slug="vm-notify"):
    """Create order with item, validate, and submit. Returns order_id."""
    resp = client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "title": "Post-Submit Integration Order",
            "business_reason": "Testing post-submit hooks",
        },
    )
    assert resp.status_code == 201
    order_id = resp.get_json()["id"]

    resp = client.post(
        f"/api/v1/orders/{order_id}/items",
        headers=headers,
        json={
            "template_slug": template_slug,
            "template_version": "1.0.0",
            "parameters": {"cpu_cores": 4},
        },
    )
    assert resp.status_code == 201

    resp = client.post(f"/api/v1/orders/{order_id}/validate", headers=headers)
    assert resp.status_code == 200

    resp = client.post(f"/api/v1/orders/{order_id}/submit", headers=headers)
    assert resp.status_code == 200
    return order_id


class TestSubmitCreatesNotification:
    def test_submit_creates_notification(
        self, submit_client, submit_session, seeded_template
    ):
        """Submitting an order must create at least one notification entry
        for the requester in the notifications table."""
        from app.data.db.models.notification import NotificationModel

        headers = _auth_header(submit_client, "test-requester")
        _create_and_submit_order(submit_client, headers)

        notifications = (
            submit_session.query(NotificationModel)
            .filter_by(recipient_id="test-requester")
            .all()
        )
        assert len(notifications) >= 1
        event_types = [n.event_type for n in notifications]
        assert "order_submitted" in event_types


class TestSubmitCreatesSubscription:
    def test_submit_creates_subscription(
        self, submit_client, submit_session, seeded_template
    ):
        """Submitting an order must create at least one subscription entry
        in the subscriptions table for the requester."""
        from app.data.db.models.subscription import SubscriptionModel

        headers = _auth_header(submit_client, "test-requester")
        _create_and_submit_order(submit_client, headers)

        subscriptions = (
            submit_session.query(SubscriptionModel)
            .filter_by(requester_id="test-requester")
            .all()
        )
        assert len(subscriptions) >= 1
        slugs = [s.template_slug for s in subscriptions]
        assert "vm-notify" in slugs

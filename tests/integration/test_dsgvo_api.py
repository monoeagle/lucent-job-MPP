# tests/integration/test_dsgvo_api.py
import pytest

from app.data.db.session import get_engine, get_session_factory, Base
from app.data.repositories.order_repository import OrderRepository
from app.services.notification_service import NotificationService


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
def seed_order(db_session):
    """Create a draft order owned by test-requester."""
    repo = OrderRepository(db_session)
    return repo.create_order(
        "test-requester",
        "DSGVO Test Order",
        "Testing anonymization",
    )


@pytest.fixture
def seed_notification(app, db_session):
    """Seed a notification for test-requester."""
    with app.app_context():
        service = NotificationService(db_session)
        return service.send(
            event_type="order_submitted",
            recipient_email="requester@test.local",
            recipient_id="test-requester",
            subject="Order Submitted",
            body="Your order has been submitted.",
        )


def _reset_dsgvo(client, admin_headers):
    """Helper: ensure DSGVO is disabled after a test."""
    client.put(
        "/api/v1/admin/dsgvo",
        headers=admin_headers,
        json={"dsgvo_anonymize": False},
    )


class TestDsgvoAdminEndpoints:
    def test_get_dsgvo_status_default_false(self, client, db_session, admin_headers):
        resp = client.get("/api/v1/admin/dsgvo", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "dsgvo_anonymize" in data
        assert data["dsgvo_anonymize"] is False

    def test_set_dsgvo_enabled(self, client, db_session, admin_headers):
        try:
            resp = client.put(
                "/api/v1/admin/dsgvo",
                headers=admin_headers,
                json={"dsgvo_anonymize": True},
            )
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["dsgvo_anonymize"] is True

            # GET should now confirm enabled
            resp = client.get("/api/v1/admin/dsgvo", headers=admin_headers)
            assert resp.status_code == 200
            assert resp.get_json()["dsgvo_anonymize"] is True
        finally:
            _reset_dsgvo(client, admin_headers)

    def test_dsgvo_requires_admin(self, client, db_session, requester_headers):
        resp_get = client.get("/api/v1/admin/dsgvo", headers=requester_headers)
        assert resp_get.status_code == 403

        resp_put = client.put(
            "/api/v1/admin/dsgvo",
            headers=requester_headers,
            json={"dsgvo_anonymize": True},
        )
        assert resp_put.status_code == 403


class TestDsgvoAnonymization:
    def test_dsgvo_anonymizes_order_list(
        self, client, db_session, seed_order, admin_headers, requester_headers
    ):
        try:
            client.put(
                "/api/v1/admin/dsgvo",
                headers=admin_headers,
                json={"dsgvo_anonymize": True},
            )

            resp = client.get("/api/v1/orders", headers=requester_headers)
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["total"] >= 1
            for item in data["items"]:
                assert "***" in item["requester_id"], (
                    f"Expected requester_id to be masked, got: {item['requester_id']}"
                )
        finally:
            _reset_dsgvo(client, admin_headers)

    def test_dsgvo_anonymizes_notifications(
        self, client, db_session, seed_notification, admin_headers, requester_headers
    ):
        try:
            client.put(
                "/api/v1/admin/dsgvo",
                headers=admin_headers,
                json={"dsgvo_anonymize": True},
            )

            resp = client.get("/api/v1/notifications", headers=requester_headers)
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["total"] >= 1
            for item in data["items"]:
                assert "***" in item["recipient_email"], (
                    f"Expected recipient_email to be masked, got: {item['recipient_email']}"
                )
        finally:
            _reset_dsgvo(client, admin_headers)

    def test_dsgvo_disabled_shows_clear_data(
        self, client, db_session, seed_order, seed_notification, admin_headers, requester_headers
    ):
        # Ensure DSGVO is off
        client.put(
            "/api/v1/admin/dsgvo",
            headers=admin_headers,
            json={"dsgvo_anonymize": False},
        )

        order_resp = client.get("/api/v1/orders", headers=requester_headers)
        assert order_resp.status_code == 200
        order_data = order_resp.get_json()
        assert order_data["total"] >= 1
        for item in order_data["items"]:
            assert item["requester_id"] == "test-requester"

        notif_resp = client.get("/api/v1/notifications", headers=requester_headers)
        assert notif_resp.status_code == 200
        notif_data = notif_resp.get_json()
        assert notif_data["total"] >= 1
        for item in notif_data["items"]:
            assert item["recipient_email"] == "requester@test.local"

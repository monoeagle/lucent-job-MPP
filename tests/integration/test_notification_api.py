# tests/integration/test_notification_api.py
import os

import pytest

from app import create_app
from app.data.db.session import get_engine, get_session_factory, Base


@pytest.fixture
def notif_app():
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
    yield app, engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def notif_client(notif_app):
    app, _ = notif_app
    return app.test_client()


@pytest.fixture
def admin_header(notif_client):
    resp = notif_client.post("/api/v1/auth/login", json={"username": "test-admin"})
    return {"Authorization": f"Bearer {resp.get_json()['token']}"}


@pytest.fixture
def requester_header(notif_client):
    resp = notif_client.post("/api/v1/auth/login", json={"username": "test-requester"})
    return {"Authorization": f"Bearer {resp.get_json()['token']}"}


@pytest.fixture
def seed_notifications(notif_app):
    """Seed notification records via the service layer."""
    app, _ = notif_app

    def _seed():
        with app.app_context():
            session = app.session_factory()
            from app.services.notification_service import NotificationService

            service = NotificationService(session)
            service.send(
                event_type="order_submitted",
                recipient_email="requester@test.local",
                recipient_id="test-requester",
                subject="Order Submitted",
                body="Your order ord-1 has been submitted.",
            )
            service.send(
                event_type="order_approved",
                recipient_email="requester@test.local",
                recipient_id="test-requester",
                subject="Order Approved",
                body="Your order ord-1 has been approved.",
            )
            service.send(
                event_type="order_submitted",
                recipient_email="admin@test.local",
                recipient_id="test-admin",
                subject="New Order",
                body="A new order has been submitted for review.",
            )
            session.close()

    return _seed


class TestAdminNotificationList:
    def test_admin_list_returns_all_notifications(self, notif_client, admin_header,
                                                    seed_notifications):
        seed_notifications()
        resp = notif_client.get("/api/v1/admin/notifications", headers=admin_header)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "items" in data
        assert "total" in data
        assert data["total"] == 3
        assert len(data["items"]) == 3

    def test_admin_list_filter_by_status(self, notif_client, admin_header,
                                          seed_notifications):
        seed_notifications()
        resp = notif_client.get(
            "/api/v1/admin/notifications?status=sent",
            headers=admin_header,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] == 3
        for item in data["items"]:
            assert item["status"] == "sent"

    def test_admin_list_pagination(self, notif_client, admin_header,
                                    seed_notifications):
        seed_notifications()
        resp = notif_client.get(
            "/api/v1/admin/notifications?limit=2&offset=0",
            headers=admin_header,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["items"]) == 2
        assert data["total"] == 3
        assert data["limit"] == 2
        assert data["offset"] == 0

    def test_admin_list_requires_admin(self, notif_client, requester_header):
        resp = notif_client.get(
            "/api/v1/admin/notifications",
            headers=requester_header,
        )
        assert resp.status_code == 403


class TestUserNotificationList:
    def test_user_list_own_notifications(self, notif_client, requester_header,
                                          seed_notifications):
        seed_notifications()
        resp = notif_client.get("/api/v1/notifications", headers=requester_header)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] == 2
        for item in data["items"]:
            assert item["recipient_id"] == "test-requester"

    def test_user_list_requires_auth(self, notif_client):
        resp = notif_client.get("/api/v1/notifications")
        assert resp.status_code == 401

    def test_admin_sees_own_notifications(self, notif_client, admin_header,
                                           seed_notifications):
        seed_notifications()
        resp = notif_client.get("/api/v1/notifications", headers=admin_header)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] == 1
        for item in data["items"]:
            assert item["recipient_id"] == "test-admin"

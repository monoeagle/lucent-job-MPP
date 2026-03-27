# tests/integration/test_notification_read_api.py
import os

import pytest

from app import create_app
from app.data.db.session import get_engine, get_session_factory, Base


@pytest.fixture
def app():
    flask_app = create_app({
        "AUTH_MODE": "stub",
        "ENV": "development",
        "TESTING": "True",
        "DATABASE_URL": os.environ.get(
            "TEST_DATABASE_URL",
            "postgresql://mpp:mpp@localhost:5432/mpp_test",
        ),
    })
    engine = get_engine(flask_app.config["DATABASE_URL"])
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield flask_app, engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def client(app):
    flask_app, _ = app
    return flask_app.test_client()


@pytest.fixture
def requester_header(client):
    resp = client.post("/api/v1/auth/login", json={"username": "test-requester"})
    return {"Authorization": f"Bearer {resp.get_json()['token']}"}


@pytest.fixture
def approver_header(client):
    resp = client.post("/api/v1/auth/login", json={"username": "test-approver"})
    return {"Authorization": f"Bearer {resp.get_json()['token']}"}


@pytest.fixture
def seed_notifications(app):
    """Seed 2 notifications for test-requester via NotificationService.send()."""
    flask_app, _ = app

    def _seed():
        with flask_app.app_context():
            from app.services.notification_service import NotificationService
            session = flask_app.session_factory()
            service = NotificationService(session)
            n1 = service.send(
                event_type="order_submitted",
                recipient_email="requester@test.local",
                recipient_id="test-requester",
                subject="Order Submitted",
                body="Your order has been submitted.",
            )
            n2 = service.send(
                event_type="order_approved",
                recipient_email="requester@test.local",
                recipient_id="test-requester",
                subject="Order Approved",
                body="Your order has been approved.",
            )
            # Capture IDs before session closes to avoid DetachedInstanceError
            n1_id, n2_id = n1.id, n2.id
            session.close()
        return n1_id, n2_id

    return _seed


class TestMarkRead:
    def test_mark_read_returns_200_with_read_at(self, client, requester_header,
                                                 seed_notifications):
        n1_id, n2_id = seed_notifications()
        resp = client.patch(
            f"/api/v1/notifications/{n1_id}/read",
            headers=requester_header,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["id"] == n1_id
        assert data["read_at"] is not None

    def test_mark_read_404_for_nonexistent(self, client, requester_header,
                                            seed_notifications):
        seed_notifications()
        resp = client.patch(
            "/api/v1/notifications/nonexistent-id/read",
            headers=requester_header,
        )
        assert resp.status_code == 404

    def test_mark_read_403_for_other_users_notification(self, client, requester_header,
                                                          app):
        flask_app, _ = app
        # Seed a notification for approver
        with flask_app.app_context():
            from app.services.notification_service import NotificationService
            session = flask_app.session_factory()
            service = NotificationService(session)
            approver_notif = service.send(
                event_type="order_submitted",
                recipient_email="approver@test.local",
                recipient_id="test-approver",
                subject="Approval Needed",
                body="An order needs approval.",
            )
            approver_notif_id = approver_notif.id
            session.close()

        # requester tries to mark approver's notification as read
        resp = client.patch(
            f"/api/v1/notifications/{approver_notif_id}/read",
            headers=requester_header,
        )
        assert resp.status_code == 403


class TestMarkAllRead:
    def test_mark_all_read_returns_200_with_marked_count(self, client, requester_header,
                                                          seed_notifications):
        seed_notifications()
        resp = client.patch("/api/v1/notifications/read-all", headers=requester_header)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["marked_count"] == 2

    def test_mark_all_read_only_marks_own_notifications(self, client, approver_header,
                                                         seed_notifications):
        # Seed is for test-requester; approver has 0 notifications
        seed_notifications()
        resp = client.patch("/api/v1/notifications/read-all", headers=approver_header)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["marked_count"] == 0


class TestUnreadCount:
    def test_unread_count_returns_2_initially(self, client, requester_header,
                                               seed_notifications):
        seed_notifications()
        resp = client.get("/api/v1/notifications/unread-count", headers=requester_header)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["count"] == 2

    def test_unread_count_decreases_after_mark_read(self, client, requester_header,
                                                      seed_notifications):
        n1_id, n2_id = seed_notifications()
        # Mark one as read
        client.patch(f"/api/v1/notifications/{n1_id}/read", headers=requester_header)
        # Count should be 1
        resp = client.get("/api/v1/notifications/unread-count", headers=requester_header)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["count"] == 1


class TestListIncludesReadAt:
    def test_list_response_includes_read_at_field(self, client, requester_header,
                                                    seed_notifications):
        seed_notifications()
        resp = client.get("/api/v1/notifications", headers=requester_header)
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["items"]) > 0
        for item in data["items"]:
            assert "read_at" in item

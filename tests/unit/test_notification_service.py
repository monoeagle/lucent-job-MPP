# tests/unit/test_notification_service.py
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone


class TestNotificationSend:
    def setup_method(self):
        self.session = MagicMock()
        from app.services.notification_service import NotificationService
        self.service = NotificationService(self.session)

    def test_send_creates_notification_record(self):
        result = self.service.send(
            event_type="order_submitted",
            recipient_email="user@test.local",
            recipient_id="user-1",
            subject="Order Submitted",
            body="Your order has been submitted.",
        )
        assert result is not None
        assert result.event_type == "order_submitted"
        assert result.recipient_email == "user@test.local"
        assert result.recipient_id == "user-1"
        assert result.subject == "Order Submitted"
        assert result.body == "Your order has been submitted."
        self.session.add.assert_called_once()
        self.session.commit.assert_called_once()

    def test_send_dev_mode_marks_as_sent(self):
        """Without SMTP configured, notification is immediately marked sent."""
        result = self.service.send(
            event_type="order_approved",
            recipient_email="user@test.local",
            recipient_id="user-1",
            subject="Approved",
            body="Your order was approved.",
        )
        assert result.status == "sent"
        assert result.sent_at is not None

    def test_send_generates_uuid_id(self):
        result = self.service.send(
            event_type="order_submitted",
            recipient_email="user@test.local",
            recipient_id=None,
            subject="Test",
            body="Test body",
        )
        assert result.id is not None
        assert len(result.id) == 36  # UUID format

    def test_send_allows_null_recipient_id(self):
        result = self.service.send(
            event_type="system_alert",
            recipient_email="admin@test.local",
            recipient_id=None,
            subject="Alert",
            body="System alert.",
        )
        assert result.recipient_id is None


class TestNotificationList:
    def setup_method(self):
        self.session = MagicMock()
        from app.services.notification_service import NotificationService
        self.service = NotificationService(self.session)

    def _make_notification(self, **kwargs):
        from app.data.db.models.notification import NotificationModel
        defaults = {
            "id": "notif-1",
            "event_type": "order_submitted",
            "recipient_email": "user@test.local",
            "recipient_id": "user-1",
            "subject": "Test",
            "body": "Test body",
            "status": "sent",
            "attempts": 0,
            "created_at": datetime.now(timezone.utc),
            "sent_at": datetime.now(timezone.utc),
            "error_message": None,
        }
        defaults.update(kwargs)
        n = NotificationModel(**defaults)
        return n

    def test_list_notifications_default(self):
        notif = self._make_notification()
        query = self.session.query.return_value
        query.order_by.return_value = query
        query.offset.return_value = query
        query.limit.return_value = query
        query.count.return_value = 1
        query.all.return_value = [notif]

        result = self.service.list_notifications()
        assert result["total"] == 1
        assert result["limit"] == 50
        assert result["offset"] == 0
        assert len(result["items"]) == 1

    def test_list_notifications_filter_by_recipient_id(self):
        query = self.session.query.return_value
        query.filter.return_value = query
        query.order_by.return_value = query
        query.offset.return_value = query
        query.limit.return_value = query
        query.count.return_value = 0
        query.all.return_value = []

        result = self.service.list_notifications(recipient_id="user-1")
        assert result["total"] == 0
        query.filter.assert_called_once()

    def test_list_notifications_filter_by_status(self):
        query = self.session.query.return_value
        query.filter.return_value = query
        query.order_by.return_value = query
        query.offset.return_value = query
        query.limit.return_value = query
        query.count.return_value = 0
        query.all.return_value = []

        result = self.service.list_notifications(status="pending")
        assert result["total"] == 0
        query.filter.assert_called_once()

    def test_list_notifications_with_pagination(self):
        query = self.session.query.return_value
        query.order_by.return_value = query
        query.offset.return_value = query
        query.limit.return_value = query
        query.count.return_value = 10
        query.all.return_value = []

        result = self.service.list_notifications(limit=5, offset=5)
        assert result["limit"] == 5
        assert result["offset"] == 5
        query.offset.assert_called_with(5)
        query.limit.assert_called_with(5)


class TestNotificationGet:
    def setup_method(self):
        self.session = MagicMock()
        from app.services.notification_service import NotificationService
        self.service = NotificationService(self.session)

    def test_get_existing_notification(self):
        from app.data.db.models.notification import NotificationModel
        notif = MagicMock(spec=NotificationModel)
        notif.id = "notif-1"
        self.session.query.return_value.filter_by.return_value.first.return_value = notif

        result = self.service.get_notification("notif-1")
        assert result is not None
        assert result.id == "notif-1"

    def test_get_nonexistent_notification(self):
        self.session.query.return_value.filter_by.return_value.first.return_value = None

        result = self.service.get_notification("no-such-id")
        assert result is None

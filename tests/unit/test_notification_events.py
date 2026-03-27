import pytest
from unittest.mock import MagicMock
from app.services.notification_service import NotificationService
from app.data.clients.email_sender import StubEmailSender


class TestCreateEventNotification:
    def setup_method(self):
        self.session = MagicMock()
        self.email_sender = StubEmailSender()
        self.service = NotificationService(self.session, email_sender=self.email_sender)

    def test_creates_order_submitted_notification(self):
        result = self.service.create_event_notification(
            event_type="order_submitted",
            recipient_id="user-1",
            recipient_email="user@test.local",
            context={"order_number": "ORD-2026-00001", "title": "My Order"},
        )
        assert result.event_type == "order_submitted"
        assert result.recipient_id == "user-1"
        assert "ORD-2026-00001" in result.subject
        self.session.add.assert_called_once()

    def test_creates_approval_requested_notification(self):
        result = self.service.create_event_notification(
            event_type="approval_requested",
            recipient_id="approver-1",
            recipient_email="approver@test.local",
            context={"order_number": "ORD-2026-00002", "requester": "user-1"},
        )
        assert result.event_type == "approval_requested"
        assert "Genehmigung" in result.subject

    def test_calls_email_sender(self):
        sender = MagicMock()
        service = NotificationService(self.session, email_sender=sender)
        service.create_event_notification(
            event_type="order_submitted",
            recipient_id="user-1",
            recipient_email="user@test.local",
            context={"order_number": "ORD-1", "title": "Test"},
        )
        sender.send.assert_called_once()

    def test_works_without_email_sender(self):
        service = NotificationService(self.session)
        result = service.create_event_notification(
            event_type="order_submitted",
            recipient_id="user-1",
            recipient_email="user@test.local",
            context={"order_number": "ORD-1", "title": "Test"},
        )
        assert result is not None

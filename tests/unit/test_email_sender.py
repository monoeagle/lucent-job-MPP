import logging
from app.data.clients.email_sender import StubEmailSender


class TestStubEmailSender:
    def test_send_logs_email(self, caplog):
        sender = StubEmailSender()
        with caplog.at_level(logging.INFO):
            sender.send("user@test.local", "Test Subject", "Test Body")
        assert "user@test.local" in caplog.text
        assert "Test Subject" in caplog.text

    def test_send_returns_true(self):
        sender = StubEmailSender()
        result = sender.send("user@test.local", "Subject", "Body")
        assert result is True

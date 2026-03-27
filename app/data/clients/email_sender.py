import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class EmailSender(ABC):
    @abstractmethod
    def send(self, to_email: str, subject: str, body: str) -> bool:
        pass


class StubEmailSender(EmailSender):
    def send(self, to_email: str, subject: str, body: str) -> bool:
        logger.info(
            "EMAIL STUB — To: %s | Subject: %s | Body: %s",
            to_email, subject, body[:200],
        )
        return True

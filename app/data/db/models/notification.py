from datetime import datetime, timezone

from sqlalchemy import Column, String, Integer, DateTime, Text, Index
from app.data.db.session import Base


class NotificationModel(Base):
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True)
    event_type = Column(String(50), nullable=False, index=True)
    recipient_email = Column(String(200), nullable=False)
    recipient_id = Column(String(100), nullable=True, index=True)
    subject = Column(String(200), nullable=False)
    body = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="pending", index=True)
    attempts = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True),
                        default=lambda: datetime.now(timezone.utc))
    sent_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)

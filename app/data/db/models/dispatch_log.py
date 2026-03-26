from datetime import datetime, timezone

from sqlalchemy import Column, String, Text, DateTime, Integer, Index
from app.data.db.session import Base


class DispatchLogModel(Base):
    __tablename__ = "dispatch_logs"

    id = Column(String(36), primary_key=True)
    order_id = Column(String(36), nullable=False, index=True)
    order_item_id = Column(String(36), nullable=False, index=True)
    job_id = Column(String(100), nullable=True)
    dispatch_method = Column(String(20), nullable=False)
    dispatched_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    attempt_count = Column(Integer, nullable=False, default=1)
    status = Column(String(20), nullable=False)
    error_message = Column(Text, nullable=True)

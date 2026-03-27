from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, Index
from sqlalchemy.dialects.postgresql import JSONB
from app.data.db.session import Base


class AuditLogModel(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True)
    timestamp = Column(DateTime(timezone=True), nullable=False,
                       default=lambda: datetime.now(timezone.utc), index=True)
    actor_id = Column(String(100), nullable=True, index=True)
    actor_type = Column(String(20), nullable=False)
    action = Column(String(50), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(String(36), nullable=True)
    details = Column(JSONB, nullable=True)
    request_id = Column(String(36), nullable=True)

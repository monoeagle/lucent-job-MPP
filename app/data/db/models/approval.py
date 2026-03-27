from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, Boolean, DateTime, Numeric, ForeignKey, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from app.data.db.session import Base


class ApprovalRuleModel(Base):
    __tablename__ = "approval_rules"

    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)
    rule_type = Column(String(20), nullable=False)
    threshold_eur = Column(Numeric(10, 2), nullable=True)
    service_type_slug = Column(String(64), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))


class ApprovalRequestModel(Base):
    __tablename__ = "approval_requests"

    id = Column(String(36), primary_key=True)
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="pending")
    approval_rule_ids = Column(JSONB, nullable=False)
    requested_at = Column(DateTime(timezone=True), nullable=False)
    deadline_at = Column(DateTime(timezone=True), nullable=False)
    decided_by = Column(String(100), nullable=True)
    decided_at = Column(DateTime(timezone=True), nullable=True)
    decision_reason = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("order_id", name="uq_approval_request_order"),
    )

from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Numeric, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.data.db.session import Base


class GroupSubscriptionModel(Base):
    __tablename__ = "group_subscriptions"

    id = Column(String(36), primary_key=True)
    order_item_group_id = Column(String(36), ForeignKey("order_item_groups.id"), nullable=True)
    name = Column(String(100), nullable=False)
    requester_id = Column(String(100), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    subscriptions = relationship("SubscriptionModel", back_populates="group_subscription")


class SubscriptionModel(Base):
    __tablename__ = "subscriptions"

    id = Column(String(36), primary_key=True)
    order_item_id = Column(String(36), ForeignKey("order_items.id"), nullable=False, unique=True)
    group_subscription_id = Column(String(36), ForeignKey("group_subscriptions.id", ondelete="SET NULL"),
                                    nullable=True, index=True)
    requester_id = Column(String(100), nullable=False, index=True)
    status = Column(String(30), nullable=False, default="ordered", index=True)
    display_name = Column(String(200), nullable=False)
    template_slug = Column(String(64), nullable=False)
    template_version = Column(String(32), nullable=False)
    parameters = Column(JSONB, nullable=False, default=dict)
    pending_changes = Column(JSONB, nullable=True)
    monthly_cost_eur = Column(Numeric(10, 2), nullable=True)
    activated_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    group_subscription = relationship("GroupSubscriptionModel", back_populates="subscriptions")

    __table_args__ = (
        Index("ix_subscription_requester_status", "requester_id", "status"),
    )

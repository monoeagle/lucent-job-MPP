from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, DateTime, Integer, UniqueConstraint, ForeignKey, Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.data.db.session import Base


class OrderModel(Base):
    __tablename__ = "orders"

    id = Column(String(36), primary_key=True)
    order_number = Column(String(20), nullable=False, unique=True)
    requester_id = Column(String(100), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="draft", index=True)
    title = Column(String(100), nullable=False)
    business_reason = Column(Text, nullable=True)
    desired_date = Column(String(10), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    metadata_ = Column("metadata", JSONB, nullable=True, default=dict)
    context = Column(JSONB, nullable=True)

    items = relationship("OrderItemModel", back_populates="order",
                         order_by="OrderItemModel.position",
                         cascade="all, delete-orphan")


class OrderItemModel(Base):
    __tablename__ = "order_items"

    id = Column(String(36), primary_key=True)
    order_id = Column(String(36), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    template_slug = Column(String(64), nullable=False)
    template_version = Column(String(32), nullable=False)
    display_name = Column(String(100), nullable=False)
    parameters = Column(JSONB, nullable=False, default=dict)
    position = Column(Integer, nullable=False, default=1)
    validation_state = Column(String(20), nullable=False, default="unchecked")
    validation_errors = Column(JSONB, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    order = relationship("OrderModel", back_populates="items")

    __table_args__ = (
        Index("ix_order_item_order_position", "order_id", "position"),
    )

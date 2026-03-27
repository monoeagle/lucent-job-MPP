from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from app.data.db.session import Base


class OrderItemGroupModel(Base):
    __tablename__ = "order_item_groups"

    id = Column(String(36), primary_key=True)
    order_id = Column(String(36), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    position = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    items = relationship("OrderItemModel", back_populates="group",
                         foreign_keys="OrderItemModel.group_id")

    __table_args__ = (
        UniqueConstraint("order_id", "name", name="uq_group_order_name"),
        Index("ix_group_order_position", "order_id", "position"),
    )

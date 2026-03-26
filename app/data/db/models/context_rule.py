from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, UniqueConstraint, Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from app.data.db.session import Base


class AvailabilityRuleModel(Base):
    __tablename__ = "availability_rules"

    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)
    template_slug = Column(String(64), nullable=False, index=True)
    rule_type = Column(String(10), nullable=False)
    conditions = Column(JSONB, nullable=False)
    priority = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))


class ContextRestrictionModel(Base):
    __tablename__ = "context_restrictions"

    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)
    template_slug = Column(String(64), nullable=True)
    parameter_key = Column(String(64), nullable=False)
    restriction_type = Column(String(20), nullable=False)
    conditions = Column(JSONB, nullable=False)
    effect = Column(JSONB, nullable=False)
    priority = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))


class UserTenantAssignmentModel(Base):
    __tablename__ = "user_tenant_assignments"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(100), nullable=False, index=True)
    tenant_id = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("user_id", "tenant_id", name="uq_user_tenant"),
    )

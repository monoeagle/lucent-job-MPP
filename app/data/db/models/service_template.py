from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, Boolean, Numeric, DateTime, UniqueConstraint, Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from app.data.db.session import Base


class ServiceTemplateModel(Base):
    __tablename__ = "service_templates"

    id = Column(String(36), primary_key=True)
    slug = Column(String(64), nullable=False, index=True)
    version = Column(String(32), nullable=False)
    type = Column(String(32), nullable=False, index=True)
    display_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(64), nullable=False, index=True)
    icon_identifier = Column(String(100), nullable=True)
    tofu_module_source = Column(String(500), nullable=False)
    parameters = Column(JSONB, nullable=False, default=list)
    cross_parameter_rules = Column(JSONB, nullable=False, default=list)
    status = Column(String(20), nullable=False, default="active", index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    deprecated_at = Column(DateTime(timezone=True), nullable=True)
    deprecated_by = Column(String(36), nullable=True)
    estimated_cost_eur_per_month = Column(Numeric(10, 2), nullable=True)
    approval_always_required = Column(Boolean, default=False, nullable=False)
    metadata_ = Column("metadata", JSONB, nullable=True, default=dict)

    __table_args__ = (
        UniqueConstraint("slug", "version", name="uq_template_slug_version"),
        Index("ix_template_slug_status", "slug", "status"),
    )

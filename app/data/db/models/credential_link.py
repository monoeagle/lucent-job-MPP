from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, Boolean, Index
from sqlalchemy.dialects.postgresql import JSONB

from app.data.db.session import Base


class CredentialLinkModel(Base):
    __tablename__ = "credential_links"

    id = Column(String(36), primary_key=True)
    order_item_id = Column(String(36), nullable=False, index=True)
    token_hash = Column(String(64), nullable=False, unique=True)
    credentials = Column(JSONB, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    accessed_at = Column(DateTime(timezone=True), nullable=True)
    is_consumed = Column(Boolean, default=False, nullable=False)

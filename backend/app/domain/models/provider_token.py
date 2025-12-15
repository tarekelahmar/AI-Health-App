from __future__ import annotations

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, UniqueConstraint, Index, Text
from app.core.database import Base


class ProviderToken(Base):
    __tablename__ = "provider_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)

    provider = Column(String(32), nullable=False, index=True)  # e.g. "whoop"
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    token_type = Column(String(32), nullable=True)  # "bearer"
    scope = Column(Text, nullable=True)

    expires_at = Column(DateTime, nullable=True)  # if provided
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_provider_tokens_user_provider"),
        Index("ix_provider_tokens_user_provider", "user_id", "provider"),
    )

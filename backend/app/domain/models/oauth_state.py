"""
OAuth state storage for CSRF protection.

Stores OAuth state tokens server-side with TTL to prevent CSRF attacks.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import Column, Integer, String, DateTime, Index
from app.core.database import Base


class OAuthState(Base):
    """OAuth state token for CSRF protection."""
    __tablename__ = "oauth_states"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    provider = Column(String(50), nullable=False)  # "whoop", etc.
    state_token = Column(String(255), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_oauth_states_user_provider", "user_id", "provider"),
    )


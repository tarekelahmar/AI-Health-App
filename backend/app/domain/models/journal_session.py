"""
Journal V3 — Session model.

A session represents one conversation between the user and the AI companion.
New session is created when:
- No session exists for today, OR
- Last message in the most recent session was >4 hours ago
"""
from datetime import datetime

from sqlalchemy import Column, Integer, Float, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


class JournalSession(Base):
    __tablename__ = "journal_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)

    # Daily score (1.0-10.0, step 0.5) — confirmed by user
    daily_score = Column(Float, nullable=True)
    score_confirmed_at = Column(DateTime, nullable=True)

    # AI-generated session summary (for context carry-forward)
    summary = Column(Text, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    messages = relationship("JournalMessage", back_populates="session", order_by="JournalMessage.created_at")

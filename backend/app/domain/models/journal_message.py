"""
Journal V3 — Message model.

Each message is a single turn in a journal conversation session.
User messages store the user's text; assistant messages store the AI response
and optionally the analysis JSON (inferred dimensions, context tags, factors).
"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


class JournalMessage(Base):
    __tablename__ = "journal_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("journal_sessions.id"), nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)

    # "user" or "assistant"
    role = Column(String, nullable=False)

    content = Column(Text, nullable=False)

    # Only populated for assistant messages — contains inferred_dimensions,
    # context_tags, factors, custom_factors from the analysis call
    ai_analysis_json = Column(JSON, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    session = relationship("JournalSession", back_populates="messages")

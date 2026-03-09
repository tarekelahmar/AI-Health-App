"""User preferences for journal companion (depth level, onboarding status)."""

from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey

from app.core.database import Base


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)

    # Journal depth level: 1=Check-in, 2=Reflective, 3=Deep Analysis
    preferred_depth_level = Column(Integer, nullable=False, default=2)

    # Onboarding completed flag
    journal_onboarded = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

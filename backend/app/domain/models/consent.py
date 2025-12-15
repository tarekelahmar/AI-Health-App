from __future__ import annotations

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Index
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


class Consent(Base):
    """
    Consent record for user onboarding.
    
    Consent must be explicit, stored as structured record, and versioned.
    """
    __tablename__ = "consents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)

    consent_version = Column(String(20), nullable=False, default="1.0")  # Version of consent form
    consent_timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Explicit consent checkboxes (all must be true)
    understands_not_medical_advice = Column(Boolean, nullable=False, default=False)
    consents_to_data_analysis = Column(Boolean, nullable=False, default=False)
    understands_recommendations_experimental = Column(Boolean, nullable=False, default=False)
    understands_can_stop_anytime = Column(Boolean, nullable=False, default=False)

    # Additional metadata
    onboarding_completed = Column(Boolean, nullable=False, default=False)
    onboarding_completed_at = Column(DateTime, nullable=True)

    # Optional: store full consent text for audit
    consent_text_json = Column(JSONB, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_consents_user_version", "user_id", "consent_version"),
    )


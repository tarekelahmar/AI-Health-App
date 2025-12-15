from __future__ import annotations

from sqlalchemy import Column, Integer, String, DateTime, JSON, Float, Index
from sqlalchemy.sql import func

from app.core.database import Base


class PersonalHealthModel(Base):
    """
    Longitudinal Memory - Stable representations of the user's health patterns.
    
    Consolidates insights from evaluations, attributions, and experiments into
    a persistent model that represents what the system has learned about the user.
    """
    __tablename__ = "personal_health_models"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)

    # Stable representations of the user
    baselines_json = Column(JSON, nullable=False, default=dict)
    sensitivities_json = Column(JSON, nullable=False, default=dict)
    drivers_json = Column(JSON, nullable=False, default=dict)
    response_patterns_json = Column(JSON, nullable=False, default=dict)

    # Confidence & coverage
    confidence_score = Column(Float, default=0.0)
    data_coverage = Column(Float, default=0.0)

    # Versioning
    model_version = Column(String, default="v1")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_personal_health_models_user", "user_id"),
    )


"""
baselines_json:
{
  "sleep_duration": {"mean": 445, "std": 38},
  "hrv_rmssd": {"mean": 52, "std": 9}
}

sensitivities_json:
{
  "melatonin": {
      "sleep_duration": {"effect_size": 0.62, "confidence": 0.81}
  },
  "alcohol_evening": {
      "hrv_rmssd": {"effect_size": -0.71, "confidence": 0.88}
  }
}

drivers_json:
{
  "primary": ["sleep_debt", "late_caffeine"],
  "secondary": ["stress_variability"]
}

response_patterns_json:
{
  "lagged_effects": {
      "melatonin": {"sleep_duration": 1},
      "exercise_evening": {"hrv_rmssd": 2}
  }
}
"""


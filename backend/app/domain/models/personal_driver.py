from __future__ import annotations

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Index

from app.core.database import Base


class PersonalDriver(Base):
    """
    Personal driver attribution findings.
    
    Identifies which inputs (behaviors, supplements, labs, interventions) 
    actually explain changes in outcomes (sleep, HRV, energy, mood) per user.
    """
    __tablename__ = "personal_drivers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)

    driver_type = Column(String(20), nullable=False)  # "behavior" | "supplement" | "intervention" | "lab_marker"
    driver_key = Column(String(100), nullable=False)  # e.g. "melatonin", "alcohol_evening"
    outcome_metric = Column(String(100), nullable=False)  # e.g. "sleep_duration", "hrv_rmssd"

    lag_days = Column(Integer, nullable=False)  # 0-7
    effect_size = Column(Float, nullable=False)  # standardized (Cohen's d or beta)
    direction = Column(String(20), nullable=False)  # "positive" | "negative" | "neutral"

    variance_explained = Column(Float, nullable=False)  # R² contribution [0-1]
    confidence = Column(Float, nullable=False)  # [0-1]
    stability = Column(Float, nullable=False)  # consistency across windows [0-1]

    sample_size = Column(Integer, nullable=False)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_personal_drivers_user_outcome", "user_id", "outcome_metric"),
        Index("ix_personal_drivers_user_driver", "user_id", "driver_key"),
        Index("ix_personal_drivers_user_created", "user_id", "created_at"),
    )


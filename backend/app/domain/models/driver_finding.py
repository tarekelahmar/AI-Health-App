from __future__ import annotations

from datetime import date, datetime
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Text, Index

from app.core.database import Base


class DriverFinding(Base):
    """
    Driver discovery findings.
    
    Detects associations like "caffeine_pm associated with worse sleep_duration next day"
    or "magnesium adherence associated with improved sleep_quality/energy".
    
    MUST NOT claim causality. Output must be phrased as "associated with".
    """
    __tablename__ = "driver_findings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)

    exposure_type = Column(String(20), nullable=False)  # "behavior" | "intervention"
    exposure_key = Column(String(100), nullable=False)  # e.g. "caffeine_pm", "magnesium_glycinate"
    metric_key = Column(String(100), nullable=False)  # e.g. "sleep_duration", "energy", "resting_hr"

    lag_days = Column(Integer, nullable=False)  # 0..3
    direction = Column(String(20), nullable=False)  # "improves" | "worsens" | "unclear"

    effect_size = Column(Float, nullable=False)  # Cohen's d or standardized delta
    confidence = Column(Float, nullable=False)  # 0..1 (clamped)
    coverage = Column(Float, nullable=False)  # 0..1

    n_exposure_days = Column(Integer, nullable=False)
    n_total_days = Column(Integer, nullable=False)

    window_start = Column(Date, nullable=False)
    window_end = Column(Date, nullable=False)

    details_json = Column(Text, nullable=True)  # JSON string with baselines, means, stds, thresholds, filters

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_driver_findings_user_created", "user_id", "created_at"),
        Index("ix_driver_findings_user_exposure_metric", "user_id", "exposure_key", "metric_key"),
    )


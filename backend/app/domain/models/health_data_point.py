"""Legacy HealthDataPoint model - kept for backward compatibility"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, JSON, Index
from datetime import datetime
from app.core.database import Base


class HealthDataPoint(Base):
    """Generic health data point - can be from wearable, lab, or manual entry"""
    __tablename__ = "health_data"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    metric_type = Column(String)  # Canonical field name: metric_type (matches baselines, wearable_samples)
    value = Column(Float)
    unit = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    source = Column(String)  # "wearable", "lab", "manual"

    # STEP R: Provenance & Quality
    data_provenance_id = Column(Integer, ForeignKey("data_provenance.id"), nullable=True)
    # Using JSON instead of JSONB for SQLite compatibility in tests
    quality_score = Column(JSON, nullable=True)  # Full quality score breakdown
    is_flagged = Column(Boolean, nullable=False, default=False)  # Quality score < 0.6

    # Performance: composite indexes aligned with hot query patterns
    # - (user_id, metric_type, timestamp): per-metric time series, baselines, loop runner
    # - (user_id, timestamp): cross-metric scans in a time window (trust, reconciliation, analytics)
    __table_args__ = (
        Index("ix_health_data_user_metric_ts", "user_id", "metric_type", "timestamp"),
        Index("ix_health_data_user_ts", "user_id", "timestamp"),
    )


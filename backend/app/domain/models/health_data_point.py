"""Legacy HealthDataPoint model - kept for backward compatibility"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from app.core.database import Base

class HealthDataPoint(Base):
    """Generic health data point - can be from wearable, lab, or manual entry"""
    __tablename__ = "health_data"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    metric_type = Column("data_type", String)  # Maps Python attribute 'metric_type' to DB column 'data_type'
    value = Column(Float)
    unit = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    source = Column(String)  # "wearable", "lab", "manual"
    
    # STEP R: Provenance & Quality
    data_provenance_id = Column(Integer, ForeignKey("data_provenance.id"), nullable=True)
    quality_score = Column(JSONB, nullable=True)  # Full quality score breakdown
    is_flagged = Column(Boolean, nullable=False, default=False)  # Quality score < 0.6


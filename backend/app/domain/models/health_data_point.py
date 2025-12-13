"""Legacy HealthDataPoint model - kept for backward compatibility"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
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


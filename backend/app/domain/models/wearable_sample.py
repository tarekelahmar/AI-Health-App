from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from datetime import datetime
from app.core.database import Base

class WearableSample(Base):
    __tablename__ = "wearable_samples"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    device_type = Column(String)  # "fitbit", "oura", "whoop"
    metric_type = Column(String)  # "sleep_duration", "hrv", "steps"
    value = Column(Float)
    unit = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    device_id = Column(String)  # Device identifier


from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from datetime import datetime
from app.core.database import Base

class Symptom(Base):
    __tablename__ = "symptoms"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    symptom_name = Column(String)  # e.g., "fatigue", "brain_fog", "joint_pain"
    severity = Column(String)  # "mild", "moderate", "severe"
    frequency = Column(String)  # "daily", "weekly", "occasional"
    notes = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)


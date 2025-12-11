from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from datetime import datetime
from app.core.database import Base

class LabResult(Base):
    __tablename__ = "lab_results"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    test_name = Column(String)  # e.g., "fasting_glucose", "HbA1c"
    value = Column(Float)
    unit = Column(String)  # "mg/dL", "mmol/L", etc.
    reference_range = Column(String)  # "70-100 mg/dL"
    timestamp = Column(DateTime, default=datetime.utcnow)
    lab_name = Column(String)  # Name of lab/facility


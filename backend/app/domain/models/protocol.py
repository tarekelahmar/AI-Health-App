from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from datetime import datetime
from app.core.database import Base

class Protocol(Base):
    __tablename__ = "protocols"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    week_number = Column(Integer)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    interventions = Column(JSON)  # List of intervention objects
    status = Column(String)  # "active", "completed", "paused"
    created_at = Column(DateTime, default=datetime.utcnow)


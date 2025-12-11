from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float
from datetime import datetime
from app.core.database import Base

class Insight(Base):
    __tablename__ = "insights"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    insight_type = Column(String)  # "dysfunction", "trend", "correlation"
    title = Column(String)
    description = Column(Text)
    confidence_score = Column(Float)  # 0.0 to 1.0
    generated_at = Column(DateTime, default=datetime.utcnow)
    metadata_json = Column(Text)  # JSON string with additional data


from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from datetime import datetime
from app.core.database import Base

class Questionnaire(Base):
    __tablename__ = "questionnaires"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    questionnaire_type = Column(String)  # "onboarding", "follow_up", "symptom_tracker"
    responses = Column(JSON)  # Store structured responses
    completed_at = Column(DateTime, default=datetime.utcnow)


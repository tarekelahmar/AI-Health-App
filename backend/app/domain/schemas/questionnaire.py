from pydantic import BaseModel
from datetime import datetime
from typing import Dict, Any

class QuestionnaireCreate(BaseModel):
    questionnaire_type: str  # "onboarding", "follow_up", "symptom_tracker"
    responses: Dict[str, Any]

class QuestionnaireResponse(BaseModel):
    id: int
    user_id: int
    questionnaire_type: str
    responses: Dict[str, Any]
    completed_at: datetime


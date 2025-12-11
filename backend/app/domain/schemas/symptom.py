from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class SymptomCreate(BaseModel):
    symptom_name: str
    severity: str  # "mild", "moderate", "severe"
    frequency: str  # "daily", "weekly", "occasional"
    notes: Optional[str] = None

class SymptomResponse(BaseModel):
    id: int
    user_id: int
    symptom_name: str
    severity: str
    frequency: str
    notes: Optional[str]
    timestamp: datetime


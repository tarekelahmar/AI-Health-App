from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class UserCreate(BaseModel):
    name: str
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    created_at: datetime

class HealthDataPointCreate(BaseModel):
    data_type: str  # "sleep_duration", "fasting_glucose", etc.
    value: float
    unit: str       # "hours", "mg/dL", etc.
    source: str     # "wearable", "lab", "manual"

class HealthDataPointResponse(BaseModel):
    id: int
    user_id: int
    data_type: str
    value: float
    unit: str
    timestamp: datetime

class HealthAssessmentResponse(BaseModel):
    id: int
    user_id: int
    dysfunction_id: str
    severity_level: str
    assessment_date: datetime
    notes: Optional[str] = None

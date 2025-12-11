from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class WearableSampleCreate(BaseModel):
    device_type: str  # "fitbit", "oura", "whoop"
    metric_type: str  # "sleep_duration", "hrv", "steps"
    value: float
    unit: str
    device_id: Optional[str] = None

class WearableSampleResponse(BaseModel):
    id: int
    user_id: int
    device_type: str
    metric_type: str
    value: float
    unit: str
    timestamp: datetime
    device_id: Optional[str]


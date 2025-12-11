from pydantic import BaseModel
from datetime import datetime
from typing import List, Dict, Any

class Intervention(BaseModel):
    dysfunction: str
    intervention_name: str
    type: str
    priority: int
    daily_actions: List[str]
    rationale: str
    adherence_target: float
    metrics_to_track: List[str]

class ProtocolResponse(BaseModel):
    id: int
    user_id: int
    week_number: int
    start_date: datetime
    end_date: datetime
    interventions: List[Dict[str, Any]]
    status: str
    created_at: datetime


from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class InsightResponse(BaseModel):
    id: int
    user_id: int
    insight_type: str  # "dysfunction", "trend", "correlation"
    title: str
    description: str
    confidence_score: float
    generated_at: datetime
    metadata_json: Optional[str] = None


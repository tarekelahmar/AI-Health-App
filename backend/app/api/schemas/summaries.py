from pydantic import BaseModel
from typing import List, Any, Optional


class InsightSummaryResponse(BaseModel):
    id: int
    user_id: int
    period: str
    summary_date: str
    headline: str
    narrative: str
    key_metrics: List[str]
    drivers: List[Any]
    interventions: List[int]
    outcomes: List[str]
    confidence: int

    class Config:
        from_attributes = True


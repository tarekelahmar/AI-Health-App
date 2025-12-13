from datetime import datetime
from typing import Optional, Dict, Literal, Union
from pydantic import BaseModel, Field

InsightStatus = Literal["detected", "evaluated", "suggested"]


class InsightEvidence(BaseModel):
    baseline_mean: Optional[float] = None
    followup_mean: Optional[float] = None
    delta: Optional[float] = None
    effect_size: Optional[float] = None
    severity_std: Optional[float] = None
    days_consistent: Optional[int] = None


class InsightResponse(BaseModel):
    id: int
    created_at: datetime
    title: str
    summary: str
    metric_key: str
    confidence: float = Field(ge=0.0, le=1.0)
    status: InsightStatus
    evidence: Dict[str, Union[float, int, None]]
    explanation: Optional[str] = None
    uncertainty: Optional[str] = None
    suggested_next_step: Optional[str] = None


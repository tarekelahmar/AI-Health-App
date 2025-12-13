from datetime import datetime
from typing import Literal, Optional, List
from pydantic import BaseModel, Field

SourceType = Literal["wearable", "lab", "questionnaire", "manual"]


class HealthDataPointIn(BaseModel):
    metric_key: str = Field(..., description="Canonical metric key, e.g. sleep_duration")
    value: float
    timestamp: datetime
    source: SourceType = "manual"
    unit: Optional[str] = None  # optional; validated/filled by registry


class HealthDataBatchIn(BaseModel):
    user_id: int
    points: List[HealthDataPointIn]


class HealthDataBatchOut(BaseModel):
    inserted: int
    rejected: int
    rejected_reasons: list[str]


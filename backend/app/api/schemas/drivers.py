from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional, Dict, Any
from pydantic import BaseModel, Field


class DriverFindingOut(BaseModel):
    id: int
    user_id: int
    exposure_type: Literal["behavior", "intervention"]
    exposure_key: str
    metric_key: str
    lag_days: int
    direction: Literal["improves", "worsens", "unclear"]
    effect_size: float
    confidence: float
    coverage: float
    n_exposure_days: int
    n_total_days: int
    window_start: date
    window_end: date
    details: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DriversResponse(BaseModel):
    count: int
    items: list[DriverFindingOut]


class GenerateDriversRequest(BaseModel):
    window_days: int = Field(28, ge=7, le=365)
    max_findings: int = Field(50, ge=1, le=200)


class PersonalDriverOut(BaseModel):
    id: int
    user_id: int
    driver_type: str
    driver_key: str
    outcome_metric: str
    lag_days: int
    effect_size: float
    direction: Literal["positive", "negative", "neutral"]
    variance_explained: float
    confidence: float
    stability: float
    sample_size: int
    created_at: datetime

    class Config:
        from_attributes = True


class PersonalDriversResponse(BaseModel):
    count: int
    items: list[PersonalDriverOut]


class TopDriversResponse(BaseModel):
    outcome_metric: str
    positive: list[PersonalDriverOut]
    negative: list[PersonalDriverOut]


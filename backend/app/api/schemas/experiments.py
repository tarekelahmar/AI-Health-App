from __future__ import annotations

from datetime import datetime

from typing import Optional, Literal

from pydantic import BaseModel, Field

Direction = Literal["up", "down", "stable"]
ExperimentStatus = Literal["active", "stopped", "completed"]


class ExperimentStart(BaseModel):
    user_id: int
    intervention_id: int
    protocol_id: Optional[int] = None
    hypothesis: Optional[str] = None
    primary_metric_key: str = Field(..., min_length=2, max_length=100)
    expected_direction: Direction
    baseline_window_days: int = Field(default=14, ge=3, le=90)
    intervention_window_days: int = Field(default=14, ge=3, le=90)


class ExperimentStop(BaseModel):
    ended_at: Optional[datetime] = None
    status: ExperimentStatus = "stopped"


class ExperimentOut(BaseModel):
    id: int
    user_id: int
    intervention_id: int
    protocol_id: Optional[int] = None
    hypothesis: Optional[str] = None
    primary_metric_key: str
    expected_direction: Direction
    baseline_window_days: int
    intervention_window_days: int
    status: ExperimentStatus
    started_at: datetime
    ended_at: Optional[datetime] = None

    class Config:
        from_attributes = True


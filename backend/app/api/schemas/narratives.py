from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


PeriodType = Literal["daily", "weekly"]


class NarrativeResponse(BaseModel):
    id: int
    user_id: int
    period_type: PeriodType
    period_start: date
    period_end: date

    title: str
    summary: str

    key_points: List[Any] = Field(default_factory=list)
    drivers: List[Dict[str, Any]] = Field(default_factory=list)
    actions: List[Dict[str, Any]] = Field(default_factory=list)
    risks: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    created_at: datetime

    class Config:
        from_attributes = True


class GenerateNarrativeRequest(BaseModel):
    user_id: int
    period_type: PeriodType = "daily"
    # For daily: date is used and period is [date,date]
    # For weekly: week_start_date is used and period is [week_start, week_start+6]
    date: Optional[date] = None
    week_start_date: Optional[date] = None
    include_llm_translation: bool = False


class NarrativeListResponse(BaseModel):
    count: int
    items: List[NarrativeResponse]


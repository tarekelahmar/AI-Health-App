from datetime import date, datetime

from typing import Optional, Dict, Any

from pydantic import BaseModel, Field, conint, confloat

Score0to10 = conint(ge=0, le=10)


class DailyCheckInCreate(BaseModel):
    user_id: int
    checkin_date: date

    sleep_quality: Optional[Score0to10] = None
    energy: Optional[Score0to10] = None
    mood: Optional[Score0to10] = None
    stress: Optional[Score0to10] = None

    notes: Optional[str] = None
    behaviors_json: Dict[str, Any] = Field(default_factory=dict)


class DailyCheckInUpdate(BaseModel):
    sleep_quality: Optional[Score0to10] = None
    energy: Optional[Score0to10] = None
    mood: Optional[Score0to10] = None
    stress: Optional[Score0to10] = None

    notes: Optional[str] = None
    behaviors_json: Optional[Dict[str, Any]] = None
    adherence_rate: Optional[confloat(ge=0.0, le=1.0)] = None


class DailyCheckInResponse(BaseModel):
    id: int
    user_id: int
    checkin_date: date

    sleep_quality: Optional[int] = None
    energy: Optional[int] = None
    mood: Optional[int] = None
    stress: Optional[int] = None

    notes: Optional[str] = None
    behaviors_json: Dict[str, Any]
    adherence_rate: Optional[float] = None

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


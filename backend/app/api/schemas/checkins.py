from datetime import date, datetime

from typing import Optional, Dict, Any

from pydantic import BaseModel, Field, confloat, conint


# ── V2 scale: 1.0–10.0 float (step 0.5 enforced by frontend) ────
Score1to10 = confloat(ge=1.0, le=10.0)

# ── V1 scale: 0–10 int (deprecated, kept for backward compat) ────
Score0to10 = conint(ge=0, le=10)


class DailyCheckInCreate(BaseModel):
    """Create/upsert a daily check-in.

    V2 form sends: overall_wellbeing, energy, mood, focus, connection (float 1.0-10.0)
    V1 form sent:  energy, mood, stress, focus, sleep_quality (int 0-10) — deprecated
    """
    user_id: int
    checkin_date: date

    # V2 slider fields (1.0-10.0 float)
    overall_wellbeing: Optional[Score1to10] = None
    energy: Optional[float] = Field(None, ge=0, le=10)  # Accepts both V1 int and V2 float
    mood: Optional[float] = Field(None, ge=0, le=10)     # Accepts both V1 int and V2 float
    focus: Optional[float] = Field(None, ge=0, le=10)    # Accepts both V1 int and V2 float
    connection: Optional[Score1to10] = None

    # V1 deprecated fields (still accepted for backward compat)
    sleep_quality: Optional[Score0to10] = None
    stress: Optional[Score0to10] = None

    notes: Optional[str] = None
    behaviors_json: Dict[str, Any] = Field(default_factory=dict)


class DailyCheckInUpdate(BaseModel):
    """Partial update of a daily check-in."""
    # V2 fields
    overall_wellbeing: Optional[Score1to10] = None
    energy: Optional[float] = Field(None, ge=0, le=10)
    mood: Optional[float] = Field(None, ge=0, le=10)
    focus: Optional[float] = Field(None, ge=0, le=10)
    connection: Optional[Score1to10] = None

    # V1 deprecated
    sleep_quality: Optional[Score0to10] = None
    stress: Optional[Score0to10] = None

    notes: Optional[str] = None
    behaviors_json: Optional[Dict[str, Any]] = None
    adherence_rate: Optional[confloat(ge=0.0, le=1.0)] = None


class DailyCheckInResponse(BaseModel):
    id: int
    user_id: int
    checkin_date: date

    # V2 slider fields
    overall_wellbeing: Optional[float] = None
    energy: Optional[float] = None
    mood: Optional[float] = None
    focus: Optional[float] = None
    connection: Optional[float] = None

    # V1 deprecated fields
    sleep_quality: Optional[int] = None
    stress: Optional[int] = None

    notes: Optional[str] = None
    behaviors_json: Dict[str, Any]
    adherence_rate: Optional[float] = None

    # AI companion fields (Phase 2)
    ai_inferred_json: Optional[Dict[str, Any]] = None
    context_tags_json: Optional[Dict[str, Any]] = None
    ai_response_text: Optional[str] = None
    discrepancy_json: Optional[Dict[str, Any]] = None
    milestone_json: Optional[Dict[str, Any]] = None

    # Entry metadata
    word_count: Optional[int] = None
    depth_level: Optional[int] = None

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


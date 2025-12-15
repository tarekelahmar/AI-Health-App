from __future__ import annotations

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel


class ConsentCreate(BaseModel):
    consent_version: str = "1.0"
    understands_not_medical_advice: bool
    consents_to_data_analysis: bool
    understands_recommendations_experimental: bool
    understands_can_stop_anytime: bool
    consent_text_json: Optional[Dict[str, Any]] = None


class ConsentResponse(BaseModel):
    id: int
    user_id: int
    consent_version: str
    consent_timestamp: datetime
    understands_not_medical_advice: bool
    consents_to_data_analysis: bool
    understands_recommendations_experimental: bool
    understands_can_stop_anytime: bool
    onboarding_completed: bool
    onboarding_completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class OnboardingCompleteRequest(BaseModel):
    pass  # Just marks completion


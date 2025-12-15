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
    # WEEK 2: Provider-scoped consent
    consents_to_whoop_ingestion: bool = False
    consents_to_fitbit_ingestion: bool = False
    consents_to_oura_ingestion: bool = False
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
    # WEEK 2: Provider-scoped consent
    consents_to_whoop_ingestion: bool
    consents_to_fitbit_ingestion: bool
    consents_to_oura_ingestion: bool
    # WEEK 2: Revocation support
    revoked_at: Optional[datetime] = None
    revocation_reason: Optional[str] = None
    onboarding_completed: bool
    onboarding_completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ConsentRevokeRequest(BaseModel):
    reason: Optional[str] = None


class OnboardingCompleteRequest(BaseModel):
    pass  # Just marks completion


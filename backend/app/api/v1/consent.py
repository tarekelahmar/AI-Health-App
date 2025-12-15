from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.schemas.consent import ConsentCreate, ConsentResponse, OnboardingCompleteRequest
from app.domain.repositories.consent_repository import ConsentRepository
from app.api.auth_mode import get_request_user_id
from app.api.router_factory import make_v1_router

router = make_v1_router(prefix="/api/v1/consent", tags=["consent"])


@router.get("", response_model=ConsentResponse)
def get_consent(
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db),
):
    """Get latest consent record for user"""
    repo = ConsentRepository(db)
    consent = repo.get_latest(user_id)
    if not consent:
        raise HTTPException(status_code=404, detail="No consent record found")
    return consent


@router.post("", response_model=ConsentResponse)
def create_consent(
    payload: ConsentCreate,
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db),
):
    """
    Create consent record.
    
    All checkboxes must be true for consent to be valid.
    """
    if not all([
        payload.understands_not_medical_advice,
        payload.consents_to_data_analysis,
        payload.understands_recommendations_experimental,
        payload.understands_can_stop_anytime,
    ]):
        raise HTTPException(
            status_code=400,
            detail="All consent checkboxes must be checked"
        )

    repo = ConsentRepository(db)
    consent = repo.create(
        user_id=user_id,
        consent_version=payload.consent_version,
        understands_not_medical_advice=payload.understands_not_medical_advice,
        consents_to_data_analysis=payload.consents_to_data_analysis,
        understands_recommendations_experimental=payload.understands_recommendations_experimental,
        understands_can_stop_anytime=payload.understands_can_stop_anytime,
        consent_text_json=payload.consent_text_json,
    )
    return consent


@router.post("/complete-onboarding", response_model=ConsentResponse)
def complete_onboarding(
    payload: OnboardingCompleteRequest,
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db),
):
    """Mark onboarding as completed"""
    repo = ConsentRepository(db)
    consent = repo.mark_onboarding_completed(user_id)
    if not consent:
        raise HTTPException(status_code=404, detail="No consent record found. Please create consent first.")
    return consent


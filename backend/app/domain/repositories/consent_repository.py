from __future__ import annotations

from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from app.domain.models.consent import Consent


class ConsentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_latest(self, user_id: int) -> Optional[Consent]:
        """Get latest consent record for user"""
        return (
            self.db.query(Consent)
            .filter(Consent.user_id == user_id)
            .order_by(Consent.consent_timestamp.desc())
            .first()
        )

    def create(
        self,
        user_id: int,
        consent_version: str,
        understands_not_medical_advice: bool,
        consents_to_data_analysis: bool,
        understands_recommendations_experimental: bool,
        understands_can_stop_anytime: bool,
        consents_to_whoop_ingestion: bool = False,
        consents_to_fitbit_ingestion: bool = False,
        consents_to_oura_ingestion: bool = False,
        consent_text_json: Optional[dict] = None,
    ) -> Consent:
        """Create new consent record"""
        consent = Consent(
            user_id=user_id,
            consent_version=consent_version,
            understands_not_medical_advice=understands_not_medical_advice,
            consents_to_data_analysis=consents_to_data_analysis,
            understands_recommendations_experimental=understands_recommendations_experimental,
            understands_can_stop_anytime=understands_can_stop_anytime,
            consents_to_whoop_ingestion=consents_to_whoop_ingestion,
            consents_to_fitbit_ingestion=consents_to_fitbit_ingestion,
            consents_to_oura_ingestion=consents_to_oura_ingestion,
            consent_text_json=consent_text_json,
        )
        self.db.add(consent)
        self.db.commit()
        self.db.refresh(consent)
        return consent
    
    def revoke(self, user_id: int, reason: Optional[str] = None) -> Optional[Consent]:
        """
        Revoke consent for a user.
        
        WEEK 2: Sets revoked_at timestamp, which blocks all future provider ingestion.
        """
        consent = self.get_latest(user_id)
        if consent:
            consent.revoked_at = datetime.utcnow()
            consent.revocation_reason = reason
            self.db.add(consent)
            self.db.commit()
            self.db.refresh(consent)
        return consent
    
    def is_consent_valid(self, user_id: int, provider: Optional[str] = None) -> bool:
        """
        Check if consent is valid (not revoked and provider-specific consent granted if provider specified).
        
        WEEK 2: Returns False if consent is revoked or provider-specific consent not granted.
        """
        consent = self.get_latest(user_id)
        if not consent:
            return False
        
        # Check if revoked
        if consent.revoked_at:
            return False
        
        # Check general data analysis consent
        if not consent.consents_to_data_analysis:
            return False
        
        # Check provider-specific consent if provider specified
        if provider:
            if provider.lower() == "whoop":
                return consent.consents_to_whoop_ingestion
            elif provider.lower() == "fitbit":
                return consent.consents_to_fitbit_ingestion
            elif provider.lower() == "oura":
                return consent.consents_to_oura_ingestion
            # Unknown provider - require general consent
            return True
        
        return True

    def mark_onboarding_completed(self, user_id: int) -> Optional[Consent]:
        """Mark onboarding as completed for user"""
        consent = self.get_latest(user_id)
        if consent:
            consent.onboarding_completed = True
            consent.onboarding_completed_at = datetime.utcnow()
            self.db.add(consent)
            self.db.commit()
            self.db.refresh(consent)
        return consent


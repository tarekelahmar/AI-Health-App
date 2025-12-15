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
            consent_text_json=consent_text_json,
        )
        self.db.add(consent)
        self.db.commit()
        self.db.refresh(consent)
        return consent

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


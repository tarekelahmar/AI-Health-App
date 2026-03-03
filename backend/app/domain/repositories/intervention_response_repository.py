"""
Intervention Response Repository - Phase 3.1

Persistence layer for intervention response history.
"""
from __future__ import annotations

from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.domain.models.intervention_response import InterventionResponse


class InterventionResponseRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        user_id: int,
        intervention_id: int,
        intervention_key: str,
        start_date: datetime,
        verdict: str,
        experiment_id: Optional[int] = None,
        end_date: Optional[datetime] = None,
        duration_days: Optional[int] = None,
        target_metrics_json: Optional[dict] = None,
        overall_effect_size: Optional[float] = None,
        overall_confidence: Optional[float] = None,
        confounders_json: Optional[list] = None,
        regime_during: Optional[str] = None,
        adherence_rate: Optional[float] = None,
        evaluation_ids_json: Optional[list] = None,
    ) -> InterventionResponse:
        """Create a new intervention response record."""
        response = InterventionResponse(
            user_id=user_id,
            intervention_id=intervention_id,
            intervention_key=intervention_key,
            experiment_id=experiment_id,
            start_date=start_date,
            end_date=end_date,
            duration_days=duration_days,
            target_metrics_json=target_metrics_json,
            overall_effect_size=overall_effect_size,
            overall_confidence=overall_confidence,
            verdict=verdict,
            confounders_json=confounders_json,
            regime_during=regime_during,
            adherence_rate=adherence_rate,
            evaluation_ids_json=evaluation_ids_json,
        )
        self.db.add(response)
        self.db.commit()
        self.db.refresh(response)
        return response

    def get_by_id(self, response_id: int) -> Optional[InterventionResponse]:
        return self.db.query(InterventionResponse).filter(
            InterventionResponse.id == response_id
        ).first()

    def list_for_user(
        self,
        user_id: int,
        intervention_key: Optional[str] = None,
        verdict: Optional[str] = None,
        limit: int = 50,
    ) -> List[InterventionResponse]:
        """List response history for a user, optionally filtered."""
        query = self.db.query(InterventionResponse).filter(
            InterventionResponse.user_id == user_id
        )
        if intervention_key:
            query = query.filter(
                InterventionResponse.intervention_key == intervention_key
            )
        if verdict:
            query = query.filter(InterventionResponse.verdict == verdict)

        return query.order_by(desc(InterventionResponse.created_at)).limit(limit).all()

    def count_for_intervention(
        self, user_id: int, intervention_key: str
    ) -> int:
        """How many times has the user tried this intervention?"""
        return (
            self.db.query(InterventionResponse)
            .filter(
                InterventionResponse.user_id == user_id,
                InterventionResponse.intervention_key == intervention_key,
            )
            .count()
        )

    def get_latest_for_intervention(
        self, user_id: int, intervention_key: str
    ) -> Optional[InterventionResponse]:
        """Get the most recent response for an intervention."""
        return (
            self.db.query(InterventionResponse)
            .filter(
                InterventionResponse.user_id == user_id,
                InterventionResponse.intervention_key == intervention_key,
            )
            .order_by(desc(InterventionResponse.created_at))
            .first()
        )

    def update_user_feedback(
        self,
        response_id: int,
        user_perceived_benefit: Optional[int] = None,
        user_notes: Optional[str] = None,
        would_recommend: Optional[int] = None,
    ) -> Optional[InterventionResponse]:
        """Update user subjective feedback on a response."""
        response = self.get_by_id(response_id)
        if not response:
            return None

        if user_perceived_benefit is not None:
            response.user_perceived_benefit = user_perceived_benefit
        if user_notes is not None:
            response.user_notes = user_notes
        if would_recommend is not None:
            response.would_recommend = would_recommend
        response.updated_at = datetime.utcnow()

        self.db.add(response)
        self.db.commit()
        self.db.refresh(response)
        return response

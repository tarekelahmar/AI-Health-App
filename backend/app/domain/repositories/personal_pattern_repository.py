"""
Personal Pattern Repository - Phase 3.2

Persistence layer for detected health patterns.
"""
from __future__ import annotations

from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.domain.models.personal_pattern import PersonalPattern


class PersonalPatternRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        user_id: int,
        pattern_type: str,
        input_signals: list,
        output_signal: str,
        relationship: Optional[dict] = None,
        current_confidence: float = 0.3,
        typical_lag_hours: Optional[float] = None,
        source_insight_ids: Optional[list] = None,
    ) -> PersonalPattern:
        """Create a new pattern (starts as hypothesis)."""
        pattern = PersonalPattern(
            user_id=user_id,
            pattern_type=pattern_type,
            input_signals_json=input_signals,
            output_signal=output_signal,
            relationship_json=relationship,
            current_confidence=current_confidence,
            times_observed=1,
            times_confirmed=0,
            typical_lag_hours=typical_lag_hours,
            status="hypothesis",
            source_insight_ids_json=source_insight_ids,
        )
        self.db.add(pattern)
        self.db.commit()
        self.db.refresh(pattern)
        return pattern

    def get_by_id(self, pattern_id: int) -> Optional[PersonalPattern]:
        return self.db.query(PersonalPattern).filter(
            PersonalPattern.id == pattern_id
        ).first()

    def find_matching(
        self,
        user_id: int,
        pattern_type: str,
        input_signals: list,
        output_signal: str,
    ) -> Optional[PersonalPattern]:
        """Find an existing pattern matching these signals."""
        candidates = (
            self.db.query(PersonalPattern)
            .filter(
                PersonalPattern.user_id == user_id,
                PersonalPattern.pattern_type == pattern_type,
                PersonalPattern.output_signal == output_signal,
                PersonalPattern.status.in_(["hypothesis", "confirmed"]),
            )
            .all()
        )
        # Match by input signals (order-independent)
        target_set = set(input_signals)
        for candidate in candidates:
            stored_signals = candidate.input_signals_json or []
            if set(stored_signals) == target_set:
                return candidate
        return None

    def list_active(
        self,
        user_id: int,
        pattern_type: Optional[str] = None,
        output_signal: Optional[str] = None,
        limit: int = 50,
    ) -> List[PersonalPattern]:
        """List active patterns (hypothesis or confirmed)."""
        query = self.db.query(PersonalPattern).filter(
            PersonalPattern.user_id == user_id,
            PersonalPattern.status.in_(["hypothesis", "confirmed"]),
        )
        if pattern_type:
            query = query.filter(PersonalPattern.pattern_type == pattern_type)
        if output_signal:
            query = query.filter(PersonalPattern.output_signal == output_signal)

        return query.order_by(desc(PersonalPattern.current_confidence)).limit(limit).all()

    def list_confirmed(
        self, user_id: int, limit: int = 50
    ) -> List[PersonalPattern]:
        """List only confirmed patterns."""
        return (
            self.db.query(PersonalPattern)
            .filter(
                PersonalPattern.user_id == user_id,
                PersonalPattern.status == "confirmed",
            )
            .order_by(desc(PersonalPattern.current_confidence))
            .limit(limit)
            .all()
        )

    def increment_observation(
        self,
        pattern_id: int,
        confirmed: bool = True,
        new_confidence: Optional[float] = None,
        relationship_update: Optional[dict] = None,
    ) -> Optional[PersonalPattern]:
        """Record a new observation of this pattern."""
        pattern = self.get_by_id(pattern_id)
        if not pattern:
            return None

        pattern.times_observed += 1
        if confirmed:
            pattern.times_confirmed += 1
            pattern.last_confirmed = datetime.utcnow()

        if new_confidence is not None:
            pattern.current_confidence = new_confidence

        if relationship_update:
            current = pattern.relationship_json or {}
            current.update(relationship_update)
            pattern.relationship_json = current

        pattern.updated_at = datetime.utcnow()
        self.db.add(pattern)
        self.db.commit()
        self.db.refresh(pattern)
        return pattern

    def update_status(
        self, pattern_id: int, new_status: str
    ) -> Optional[PersonalPattern]:
        """Change pattern status."""
        pattern = self.get_by_id(pattern_id)
        if not pattern:
            return None

        pattern.status = new_status
        pattern.updated_at = datetime.utcnow()
        self.db.add(pattern)
        self.db.commit()
        self.db.refresh(pattern)
        return pattern

from __future__ import annotations

from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.domain.models.decision_signal import DecisionSignal


class DecisionSignalRepository:
    def __init__(self, db: Session):
        self.db = db

    def upsert_signal(self, signal: DecisionSignal) -> DecisionSignal:
        """Upsert a decision signal"""
        existing = (
            self.db.query(DecisionSignal)
            .filter(
                DecisionSignal.user_id == signal.user_id,
                DecisionSignal.source_type == signal.source_type,
                DecisionSignal.source_id == signal.source_id,
            )
            .first()
        )

        if existing:
            # Update existing
            existing.level = signal.level
            existing.level_name = signal.level_name
            existing.confidence = signal.confidence
            existing.evidence_count = signal.evidence_count
            existing.last_confirmed_at = signal.last_confirmed_at
            existing.confidence_explanation_json = signal.confidence_explanation_json
            existing.allowed_actions = signal.allowed_actions
            existing.language_constraints = signal.language_constraints
            existing.is_suppressed = signal.is_suppressed
            existing.suppression_reason = signal.suppression_reason
            existing.suppression_until = signal.suppression_until
            self.db.add(existing)
            self.db.commit()
            self.db.refresh(existing)
            return existing

        self.db.add(signal)
        self.db.commit()
        self.db.refresh(signal)
        return signal

    def get_by_source(
        self,
        user_id: int,
        source_type: str,
        source_id: int,
    ) -> Optional[DecisionSignal]:
        """Get decision signal for a source"""
        return (
            self.db.query(DecisionSignal)
            .filter(
                DecisionSignal.user_id == user_id,
                DecisionSignal.source_type == source_type,
                DecisionSignal.source_id == source_id,
            )
            .first()
        )

    def list_active(
        self,
        user_id: int,
        level: Optional[int] = None,
        limit: int = 100,
    ) -> List[DecisionSignal]:
        """List active (non-suppressed) decision signals"""
        query = (
            self.db.query(DecisionSignal)
            .filter(
                DecisionSignal.user_id == user_id,
                DecisionSignal.is_suppressed == False,
            )
        )
        
        if level:
            query = query.filter(DecisionSignal.level == level)
        
        return query.order_by(DecisionSignal.confidence.desc()).limit(limit).all()


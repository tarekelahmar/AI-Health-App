from __future__ import annotations

from datetime import date
from typing import Optional, List, Any

from sqlalchemy.orm import Session

from app.domain.models.narrative import Narrative
from app.core.invariants import validate_narrative_invariants, InvariantViolation


class NarrativeRepository:
    def __init__(self, db: Session):
        self.db = db

    def upsert(
        self,
        *,
        user_id: int,
        period_type: str,
        period_start: date,
        period_end: date,
        title: str,
        summary: str,
        key_points_json: List[Any],
        drivers_json: List[Any],
        actions_json: List[Any],
        risks_json: List[Any],
        metadata_json: Any,
    ) -> Narrative:
        # X1: Validate invariants before creation/update
        try:
            validate_narrative_invariants(
                user_id=user_id,
                title=title,
                summary=summary,
                key_points_json=key_points_json,
                drivers_json=drivers_json,
                risks_json=risks_json,
            )
        except InvariantViolation as e:
            # Hard-fail: skip object creation and surface safe fallback message
            raise ValueError(f"Narrative creation blocked: {e.message}")
        
        existing = (
            self.db.query(Narrative)
            .filter(Narrative.user_id == user_id)
            .filter(Narrative.period_type == period_type)
            .filter(Narrative.period_start == period_start)
            .filter(Narrative.period_end == period_end)
            .first()
        )
        if existing:
            existing.title = title
            existing.summary = summary
            existing.key_points_json = key_points_json
            existing.drivers_json = drivers_json
            existing.actions_json = actions_json
            existing.risks_json = risks_json
            existing.metadata_json = metadata_json
            self.db.add(existing)
            self.db.commit()
            self.db.refresh(existing)
            return existing

        obj = Narrative(
            user_id=user_id,
            period_type=period_type,
            period_start=period_start,
            period_end=period_end,
            title=title,
            summary=summary,
            key_points_json=key_points_json,
            drivers_json=drivers_json,
            actions_json=actions_json,
            risks_json=risks_json,
            metadata_json=metadata_json,
        )
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def get_for_period(
        self,
        *,
        user_id: int,
        period_type: str,
        period_start: date,
        period_end: date,
    ) -> Optional[Narrative]:
        return (
            self.db.query(Narrative)
            .filter(Narrative.user_id == user_id)
            .filter(Narrative.period_type == period_type)
            .filter(Narrative.period_start == period_start)
            .filter(Narrative.period_end == period_end)
            .first()
        )

    def list_recent(self, *, user_id: int, period_type: str, limit: int = 14) -> List[Narrative]:
        return (
            self.db.query(Narrative)
            .filter(Narrative.user_id == user_id)
            .filter(Narrative.period_type == period_type)
            .order_by(Narrative.created_at.desc())
            .limit(limit)
            .all()
        )


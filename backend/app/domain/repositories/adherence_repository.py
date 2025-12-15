from __future__ import annotations

from typing import List

from sqlalchemy.orm import Session

from app.domain.models.adherence_event import AdherenceEvent


class AdherenceRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, obj: AdherenceEvent) -> AdherenceEvent:
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def list_by_experiment(self, experiment_id: int, limit: int = 500) -> List[AdherenceEvent]:
        return (
            self.db.query(AdherenceEvent)
            .filter(AdherenceEvent.experiment_id == experiment_id)
            .order_by(AdherenceEvent.timestamp.desc())
            .limit(limit)
            .all()
        )


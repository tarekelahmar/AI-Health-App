from __future__ import annotations

from datetime import datetime

from typing import List, Optional

from sqlalchemy.orm import Session

from app.domain.models.experiment import Experiment


class ExperimentRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, obj: Experiment) -> Experiment:
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def get(self, experiment_id: int) -> Optional[Experiment]:
        return self.db.query(Experiment).filter(Experiment.id == experiment_id).first()

    def list_by_user(self, user_id: int, limit: int = 100) -> List[Experiment]:
        return (
            self.db.query(Experiment)
            .filter(Experiment.user_id == user_id)
            .order_by(Experiment.started_at.desc())
            .limit(limit)
            .all()
        )

    def stop(self, experiment_id: int, status: str = "stopped", ended_at: Optional[datetime] = None) -> Optional[Experiment]:
        exp = self.get(experiment_id)
        if not exp:
            return None
        exp.status = status
        exp.ended_at = ended_at or datetime.utcnow()
        self.db.commit()
        self.db.refresh(exp)
        return exp

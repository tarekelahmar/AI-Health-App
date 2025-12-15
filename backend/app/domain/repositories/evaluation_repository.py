from __future__ import annotations

from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session

from app.domain.models.evaluation_result import EvaluationResult
from app.core.invariants import validate_evaluation_invariants, InvariantViolation


class EvaluationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, obj: EvaluationResult) -> EvaluationResult:
        # X1: Validate invariants before creation
        details_json = obj.details_json if isinstance(obj.details_json, dict) else {}
        try:
            validate_evaluation_invariants(
                user_id=obj.user_id,
                experiment_id=obj.experiment_id,
                metric_key=obj.metric_key,
                verdict=obj.verdict,
                baseline_mean=obj.baseline_mean,
                baseline_std=obj.baseline_std,
                intervention_mean=obj.intervention_mean,
                intervention_std=obj.intervention_std,
                coverage=obj.coverage,
                details_json=details_json,
            )
        except InvariantViolation as e:
            # Hard-fail: skip object creation and surface safe fallback message
            raise ValueError(f"Evaluation creation blocked: {e.message}")
        
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def get_latest_for_experiment(self, experiment_id: int) -> Optional[EvaluationResult]:
        return (
            self.db.query(EvaluationResult)
            .filter(EvaluationResult.experiment_id == experiment_id)
            .order_by(EvaluationResult.created_at.desc())
            .first()
        )

    def list_by_user(self, user_id: int, limit: int = 100) -> List[EvaluationResult]:
        return (
            self.db.query(EvaluationResult)
            .filter(EvaluationResult.user_id == user_id)
            .order_by(EvaluationResult.created_at.desc())
            .limit(limit)
            .all()
        )


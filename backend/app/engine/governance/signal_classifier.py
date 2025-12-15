from __future__ import annotations

from typing import Optional
from sqlalchemy.orm import Session

from app.domain.models.insight import Insight
from app.domain.models.personal_driver import PersonalDriver
from app.domain.models.evaluation_result import EvaluationResult
from app.domain.repositories.decision_signal_repository import DecisionSignalRepository
from app.engine.governance.claim_policy import get_policy
from app.engine.governance.confidence_explanation import ConfidenceExplanationService


class SignalClassifier:
    """
    Classifies signals into confidence hierarchy levels (1-5).
    
    LEVEL 1 — Observational: Pure signals (trend, instability)
    LEVEL 2 — Correlational: Cross-signal association
    LEVEL 3 — Attributed: Lagged, behavior-linked effects
    LEVEL 4 — Evaluated: Intervention tested with baseline vs intervention
    LEVEL 5 — Reconfirmed: Repeated across multiple cycles
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.signal_repo = DecisionSignalRepository(db)
    
    def classify_insight(self, insight: Insight) -> tuple[int, str]:
        """
        Classify an insight into confidence hierarchy level.
        
        Returns:
            (level, level_name)
        """
        insight_type = insight.insight_type or "change"
        metadata = insight.metadata_json if isinstance(insight.metadata_json, dict) else {}
        
        # LEVEL 1 — Observational (trend, instability, change detection)
        if insight_type in ("trend", "instability", "change"):
            if not metadata.get("driver_key") and not metadata.get("intervention_id"):
                return 1, "observational"
        
        # LEVEL 2 — Correlational (cross-signal association)
        if metadata.get("correlation") or metadata.get("association"):
            return 2, "correlational"
        
        # LEVEL 3 — Attributed (lagged, behavior-linked)
        if metadata.get("driver_key") or metadata.get("lag_days"):
            return 3, "attributed"
        
        # Default to observational
        return 1, "observational"
    
    def classify_driver(self, driver: PersonalDriver) -> tuple[int, str]:
        """Classify a personal driver into confidence hierarchy level"""
        # Personal drivers are always LEVEL 3 — Attributed
        return 3, "attributed"
    
    def classify_evaluation(self, evaluation: EvaluationResult) -> tuple[int, str]:
        """Classify an evaluation result into confidence hierarchy level"""
        # Check if this effect has been confirmed multiple times
        from app.domain.repositories.evaluation_repository import EvaluationRepository
        
        eval_repo = EvaluationRepository(self.db)
        similar_evals = eval_repo.list_by_user_and_metric(
            user_id=evaluation.user_id,
            metric_key=evaluation.metric_key,
            limit=10,
        )
        
        # Count how many times this verdict has occurred
        same_verdict_count = sum(
            1 for e in similar_evals
            if e.verdict == evaluation.verdict and e.id != evaluation.id
        )
        
        if same_verdict_count >= 2:
            # LEVEL 5 — Reconfirmed
            return 5, "reconfirmed"
        else:
            # LEVEL 4 — Evaluated
            return 4, "evaluated"
    
    def create_decision_signal(
        self,
        user_id: int,
        source_type: str,
        source_id: int,
        level: int,
        level_name: str,
        confidence: float,
        confidence_explanation: Optional[dict] = None,
    ) -> DecisionSignal:
        """Create a decision signal with governance metadata"""
        policy = get_policy(level)
        
        signal = DecisionSignal(
            user_id=user_id,
            source_type=source_type,
            source_id=source_id,
            level=level,
            level_name=level_name,
            confidence=confidence,
            evidence_count=1,
            last_confirmed_at=datetime.utcnow(),
            confidence_explanation_json=confidence_explanation,
            allowed_actions=policy.allowed_actions,
            language_constraints={
                "must_use": policy.must_use_phrases,
                "must_not_use": policy.must_not_use_phrases,
            },
        )
        
        return self.signal_repo.upsert_signal(signal)


from datetime import datetime  # noqa: E402


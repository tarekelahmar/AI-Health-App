from __future__ import annotations

import logging
from typing import Optional
from sqlalchemy.orm import Session

from app.domain.models.evaluation_result import EvaluationResult
from app.domain.models.intervention import Intervention
from app.domain.repositories.causal_memory_repository import CausalMemoryRepository

logger = logging.getLogger(__name__)


class CausalMemoryUpdater:
    """
    Updates causal memory after each EvaluationResult.
    
    - Promotes tentative → confirmed after repeated evidence
    - Downgrades confidence when contradictory evidence appears
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.memory_repo = CausalMemoryRepository(db)
    
    def update_from_evaluation(self, evaluation: EvaluationResult) -> None:
        """
        Update causal memory from an evaluation result.
        
        Extracts driver information from the evaluation's experiment/intervention
        and updates or creates causal memory entries.
        """
        # Get the intervention associated with this evaluation
        # EvaluationResult should have experiment_id, which links to Experiment, which links to Intervention
        from app.domain.models.experiment import Experiment
        
        experiment = (
            self.db.query(Experiment)
            .filter(Experiment.id == evaluation.experiment_id)
            .first()
        )
        
        if not experiment:
            logger.warning(f"Evaluation {evaluation.id} has no associated experiment")
            return
        
        intervention = (
            self.db.query(Intervention)
            .filter(Intervention.id == experiment.intervention_id)
            .first()
        )
        
        if not intervention:
            logger.warning(f"Experiment {experiment.id} has no associated intervention")
            return
        
        # Determine driver type and key
        driver_type = self._infer_driver_type(intervention)
        driver_key = intervention.key
        
        # Determine direction from verdict
        direction = self._verdict_to_direction(evaluation.verdict)
        
        # Get effect size from evaluation
        effect_size = evaluation.effect_size or 0.0
        
        # Get confidence from evaluation
        confidence = evaluation.confidence or 0.5
        
        # Check for contradictory evidence
        existing_memory = self.memory_repo.get_for_driver_metric(
            user_id=evaluation.user_id,
            driver_key=driver_key,
            metric_key=evaluation.metric_key,
        )
        
        if existing_memory:
            # Check if this contradicts existing memory
            if existing_memory.direction != direction and existing_memory.direction != "mixed":
                if existing_memory.status == "confirmed" and existing_memory.evidence_count >= 3:
                    # Strong contradictory evidence - deprecate old memory
                    logger.info(
                        f"Contradictory evidence for {driver_key} -> {evaluation.metric_key}. "
                        f"Old: {existing_memory.direction}, New: {direction}. Deprecating old memory."
                    )
                    self.memory_repo.deprecate_contradictory(
                        user_id=evaluation.user_id,
                        driver_key=driver_key,
                        metric_key=evaluation.metric_key,
                        reason=f"Contradicted by evaluation {evaluation.id}",
                    )
                    # Create new memory with new direction
                    self.memory_repo.upsert_from_evaluation(
                        user_id=evaluation.user_id,
                        driver_type=driver_type,
                        driver_key=driver_key,
                        metric_key=evaluation.metric_key,
                        direction=direction,
                        effect_size=effect_size,
                        evaluation_id=evaluation.id,
                        confidence=confidence,
                    )
                else:
                    # Weak contradictory evidence - mark as mixed
                    logger.info(
                        f"Mixed evidence for {driver_key} -> {evaluation.metric_key}. "
                        f"Marking as mixed."
                    )
                    self.memory_repo.upsert_from_evaluation(
                        user_id=evaluation.user_id,
                        driver_type=driver_type,
                        driver_key=driver_key,
                        metric_key=evaluation.metric_key,
                        direction="mixed",
                        effect_size=effect_size,
                        evaluation_id=evaluation.id,
                        confidence=confidence * 0.7,  # Reduce confidence for mixed
                    )
            else:
                # Consistent evidence - update normally
                self.memory_repo.upsert_from_evaluation(
                    user_id=evaluation.user_id,
                    driver_type=driver_type,
                    driver_key=driver_key,
                    metric_key=evaluation.metric_key,
                    direction=direction,
                    effect_size=effect_size,
                    evaluation_id=evaluation.id,
                    confidence=confidence,
                )
        else:
            # New memory entry
            self.memory_repo.upsert_from_evaluation(
                user_id=evaluation.user_id,
                driver_type=driver_type,
                driver_key=driver_key,
                metric_key=evaluation.metric_key,
                direction=direction,
                effect_size=effect_size,
                evaluation_id=evaluation.id,
                confidence=confidence,
            )
    
    def _infer_driver_type(self, intervention: Intervention) -> str:
        """Infer driver type from intervention"""
        key_lower = intervention.key.lower()
        
        if any(x in key_lower for x in ["vitamin", "supplement", "magnesium", "melatonin", "omega"]):
            return "supplement"
        elif any(x in key_lower for x in ["sleep", "bedtime", "wake"]):
            return "sleep"
        elif any(x in key_lower for x in ["exercise", "workout", "run", "gym"]):
            return "exercise"
        elif any(x in key_lower for x in ["caffeine", "alcohol", "meditation", "stress"]):
            return "behavior"
        else:
            return "behavior"  # Default
    
    def _verdict_to_direction(self, verdict: str) -> str:
        """Convert evaluation verdict to direction"""
        verdict_lower = verdict.lower()
        
        if "helpful" in verdict_lower or "positive" in verdict_lower:
            return "improves"
        elif "harmful" in verdict_lower or "negative" in verdict_lower:
            return "worsens"
        else:
            return "mixed"


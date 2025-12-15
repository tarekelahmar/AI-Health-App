from __future__ import annotations

from typing import List, Any, Dict
from sqlalchemy.orm import Session

from app.domain.repositories.personal_health_model_repository import PersonalHealthModelRepository
from app.domain.models.evaluation_result import EvaluationResult


class PersonalModelUpdater:
    """
    Updates long-term memory from evaluations + attribution results.
    
    Consolidates insights into a stable PersonalHealthModel that represents
    what the system has learned about the user over time.
    """

    def __init__(self, db: Session):
        self.repo = PersonalHealthModelRepository(db)
        self.db = db

    def update_from_evaluation(
        self,
        user_id: int,
        evaluation: EvaluationResult,
        attribution_results: List[Any],
    ) -> Any:
        """
        Update personal health model from an evaluation and its attribution results.
        
        Args:
            user_id: User ID
            evaluation: EvaluationResult object
            attribution_results: List of attribution results (objects with metric_key, intervention_id, effect_size, confidence)
        """
        model = self.repo.get_or_create(user_id)

        # Update sensitivities from attribution results
        for attr in attribution_results:
            metric = getattr(attr, "metric_key", None) or getattr(attr, "outcome_metric", None)
            intervention = getattr(attr, "intervention_id", None) or getattr(attr, "driver_key", None)
            effect_size = getattr(attr, "effect_size", 0.0)
            confidence = getattr(attr, "confidence", 0.0)

            if not metric or not intervention:
                continue

            if not model.sensitivities_json:
                model.sensitivities_json = {}
            
            if intervention not in model.sensitivities_json:
                model.sensitivities_json[intervention] = {}
            
            model.sensitivities_json[intervention][metric] = {
                "effect_size": float(effect_size),
                "confidence": float(confidence),
            }

        # Update drivers (rank by effect magnitude)
        if attribution_results:
            sorted_drivers = sorted(
                attribution_results,
                key=lambda x: abs(getattr(x, "effect_size", 0.0)),
                reverse=True
            )

            model.drivers_json = {
                "primary": [
                    getattr(d, "intervention_id", None) or getattr(d, "driver_key", None)
                    for d in sorted_drivers[:2]
                    if getattr(d, "intervention_id", None) or getattr(d, "driver_key", None)
                ],
                "secondary": [
                    getattr(d, "intervention_id", None) or getattr(d, "driver_key", None)
                    for d in sorted_drivers[2:5]
                    if getattr(d, "intervention_id", None) or getattr(d, "driver_key", None)
                ],
            }

        # Update confidence (average of attribution confidences)
        if attribution_results:
            model.confidence_score = min(
                1.0,
                sum(getattr(a, "confidence", 0.0) for a in attribution_results) / max(len(attribution_results), 1)
            )

        # Update response patterns (lagged effects)
        if not model.response_patterns_json:
            model.response_patterns_json = {}
        
        if "lagged_effects" not in model.response_patterns_json:
            model.response_patterns_json["lagged_effects"] = {}
        
        for attr in attribution_results:
            intervention = getattr(attr, "intervention_id", None) or getattr(attr, "driver_key", None)
            metric = getattr(attr, "metric_key", None) or getattr(attr, "outcome_metric", None)
            lag_days = getattr(attr, "lag_days", 0)
            
            if intervention and metric:
                if intervention not in model.response_patterns_json["lagged_effects"]:
                    model.response_patterns_json["lagged_effects"][intervention] = {}
                model.response_patterns_json["lagged_effects"][intervention][metric] = lag_days

        self.repo.update(model)
        return model

    def update_baselines(
        self,
        user_id: int,
        baselines: Dict[str, Dict[str, float]],
    ) -> Any:
        """
        Update baselines in the personal health model.
        
        Args:
            user_id: User ID
            baselines: Dict mapping metric_key to {"mean": float, "std": float}
        """
        model = self.repo.get_or_create(user_id)
        
        if not model.baselines_json:
            model.baselines_json = {}
        
        # Merge new baselines with existing
        model.baselines_json.update(baselines)
        
        self.repo.update(model)
        return model


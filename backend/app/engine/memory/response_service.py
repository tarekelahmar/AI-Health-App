"""
Personal Response Service - Phase 3.1

The intelligence layer for intervention memory. Answers:
- "What happened when this user tried X before?"
- "What about similar interventions?"
- "Based on history, how likely is X to help?"

This service bridges the gap between raw EvaluationResults and
user-facing guidance. It accumulates learning over time.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict

from sqlalchemy.orm import Session

from app.domain.models.intervention_response import InterventionResponse
from app.domain.models.causal_memory import CausalMemory
from app.domain.repositories.intervention_response_repository import (
    InterventionResponseRepository,
)
from app.domain.repositories.causal_memory_repository import CausalMemoryRepository

logger = logging.getLogger(__name__)

# Intervention similarity groups — interventions that share mechanisms
SIMILARITY_GROUPS: Dict[str, List[str]] = {
    "magnesium": [
        "magnesium_glycinate", "magnesium_threonate",
        "magnesium_citrate", "magnesium_oxide",
    ],
    "sleep_hygiene": [
        "blue_light_blocking", "consistent_bedtime",
        "cool_bedroom", "no_screens_before_bed",
    ],
    "adaptogens": [
        "ashwagandha", "rhodiola", "holy_basil",
        "lions_mane", "reishi",
    ],
    "omega_3": ["fish_oil", "krill_oil", "algae_omega3"],
    "exercise_timing": [
        "morning_exercise", "evening_exercise",
        "no_late_exercise",
    ],
    "caffeine_management": [
        "no_caffeine_after_noon", "caffeine_reduction",
        "caffeine_cycling",
    ],
    "stress_reduction": [
        "meditation", "breathwork", "yoga",
        "cold_exposure", "sauna",
    ],
}

# Reverse map for fast lookup
_INTERVENTION_TO_GROUP: Dict[str, str] = {}
for group, members in SIMILARITY_GROUPS.items():
    for member in members:
        _INTERVENTION_TO_GROUP[member] = group


@dataclass(frozen=True)
class ResponseHistory:
    """Summary of all times a user tried an intervention."""
    intervention_key: str
    times_tried: int
    verdicts: List[str]
    avg_effect_size: Optional[float]
    avg_confidence: Optional[float]
    most_recent_verdict: Optional[str]
    most_recent_date: Optional[datetime]
    user_perceived_benefit_avg: Optional[float]
    responses: List[InterventionResponse]


@dataclass(frozen=True)
class SimilarResponse:
    """A response from a similar intervention."""
    intervention_key: str
    similarity_group: str
    verdict: str
    effect_size: Optional[float]
    confidence: Optional[float]


@dataclass(frozen=True)
class ResponsePrediction:
    """Prediction of how a user will respond to an intervention."""
    intervention_key: str
    predicted_verdict: str  # helpful | not_helpful | unclear | no_data
    predicted_effect_size: Optional[float]
    confidence: float  # How confident we are in this prediction
    basis: str  # What the prediction is based on
    prior_responses: int  # How many prior responses inform this
    similar_responses: int  # How many similar-intervention responses


class PersonalResponseService:
    """
    Answers questions about a user's intervention history.

    Combines direct response history with causal memory
    and similarity reasoning.
    """

    def __init__(self, db: Session):
        self.db = db
        self.response_repo = InterventionResponseRepository(db)
        self.memory_repo = CausalMemoryRepository(db)

    def get_response_history(
        self,
        user_id: int,
        intervention_key: str,
    ) -> ResponseHistory:
        """What happened when this user tried this before?"""
        responses = self.response_repo.list_for_user(
            user_id=user_id,
            intervention_key=intervention_key,
        )

        if not responses:
            return ResponseHistory(
                intervention_key=intervention_key,
                times_tried=0,
                verdicts=[],
                avg_effect_size=None,
                avg_confidence=None,
                most_recent_verdict=None,
                most_recent_date=None,
                user_perceived_benefit_avg=None,
                responses=[],
            )

        verdicts = [r.verdict for r in responses]
        effect_sizes = [r.overall_effect_size for r in responses if r.overall_effect_size is not None]
        confidences = [r.overall_confidence for r in responses if r.overall_confidence is not None]
        benefits = [r.user_perceived_benefit for r in responses if r.user_perceived_benefit is not None]

        return ResponseHistory(
            intervention_key=intervention_key,
            times_tried=len(responses),
            verdicts=verdicts,
            avg_effect_size=sum(effect_sizes) / len(effect_sizes) if effect_sizes else None,
            avg_confidence=sum(confidences) / len(confidences) if confidences else None,
            most_recent_verdict=responses[0].verdict,
            most_recent_date=responses[0].end_date or responses[0].start_date,
            user_perceived_benefit_avg=sum(benefits) / len(benefits) if benefits else None,
            responses=responses,
        )

    def get_similar_interventions(
        self,
        user_id: int,
        intervention_key: str,
    ) -> List[SimilarResponse]:
        """What about similar interventions the user has tried?"""
        group = _INTERVENTION_TO_GROUP.get(intervention_key)
        if not group:
            return []

        similar_keys = [
            k for k in SIMILARITY_GROUPS.get(group, [])
            if k != intervention_key
        ]

        results = []
        for key in similar_keys:
            responses = self.response_repo.list_for_user(
                user_id=user_id,
                intervention_key=key,
                limit=1,
            )
            if responses:
                r = responses[0]
                results.append(SimilarResponse(
                    intervention_key=key,
                    similarity_group=group,
                    verdict=r.verdict,
                    effect_size=r.overall_effect_size,
                    confidence=r.overall_confidence,
                ))

        return results

    def predict_response(
        self,
        user_id: int,
        intervention_key: str,
    ) -> ResponsePrediction:
        """Based on history, how likely is this to help?"""
        # 1. Check direct history
        history = self.get_response_history(user_id, intervention_key)
        if history.times_tried >= 2:
            # Strong basis — user has tried this multiple times
            helpful_count = sum(1 for v in history.verdicts if v == "helpful")
            ratio = helpful_count / len(history.verdicts)
            if ratio >= 0.6:
                predicted = "helpful"
            elif ratio <= 0.3:
                predicted = "not_helpful"
            else:
                predicted = "unclear"

            return ResponsePrediction(
                intervention_key=intervention_key,
                predicted_verdict=predicted,
                predicted_effect_size=history.avg_effect_size,
                confidence=min(0.95, 0.5 + 0.1 * history.times_tried),
                basis="direct_history",
                prior_responses=history.times_tried,
                similar_responses=0,
            )

        # 2. Check causal memory
        memories = self.memory_repo.list_by_user(user_id=user_id)
        matching = [
            m for m in memories
            if m.driver_key == intervention_key and m.status != "deprecated"
        ]
        if matching:
            mem = matching[0]
            if mem.direction == "improves":
                predicted = "helpful"
            elif mem.direction == "worsens":
                predicted = "not_helpful"
            else:
                predicted = "unclear"

            return ResponsePrediction(
                intervention_key=intervention_key,
                predicted_verdict=predicted,
                predicted_effect_size=mem.avg_effect_size,
                confidence=mem.confidence * 0.8,  # Discount — causal memory is indirect
                basis="causal_memory",
                prior_responses=history.times_tried,
                similar_responses=0,
            )

        # 3. Check similar interventions
        similar = self.get_similar_interventions(user_id, intervention_key)
        if similar:
            helpful = sum(1 for s in similar if s.verdict == "helpful")
            not_helpful = sum(1 for s in similar if s.verdict == "not_helpful")

            if helpful > not_helpful:
                predicted = "helpful"
            elif not_helpful > helpful:
                predicted = "not_helpful"
            else:
                predicted = "unclear"

            avg_effect = None
            effects = [s.effect_size for s in similar if s.effect_size is not None]
            if effects:
                avg_effect = sum(effects) / len(effects)

            return ResponsePrediction(
                intervention_key=intervention_key,
                predicted_verdict=predicted,
                predicted_effect_size=avg_effect,
                confidence=0.3 + 0.05 * len(similar),  # Low — based on similar, not direct
                basis="similar_interventions",
                prior_responses=history.times_tried,
                similar_responses=len(similar),
            )

        # 4. No data
        return ResponsePrediction(
            intervention_key=intervention_key,
            predicted_verdict="no_data",
            predicted_effect_size=None,
            confidence=0.0,
            basis="no_data",
            prior_responses=0,
            similar_responses=0,
        )

    def record_response_from_evaluation(
        self,
        user_id: int,
        intervention_id: int,
        intervention_key: str,
        experiment_id: int,
        start_date: datetime,
        end_date: datetime,
        target_metrics: Dict[str, dict],
        verdict: str,
        overall_effect_size: float,
        overall_confidence: float,
        adherence_rate: Optional[float] = None,
        confounders: Optional[List[str]] = None,
        evaluation_ids: Optional[List[int]] = None,
    ) -> InterventionResponse:
        """
        Record a response from a completed evaluation.

        Called by the evaluation pipeline after verdicts are computed.
        """
        duration = (end_date - start_date).days if end_date else None

        return self.response_repo.create(
            user_id=user_id,
            intervention_id=intervention_id,
            intervention_key=intervention_key,
            experiment_id=experiment_id,
            start_date=start_date,
            end_date=end_date,
            duration_days=duration,
            target_metrics_json=target_metrics,
            verdict=verdict,
            overall_effect_size=overall_effect_size,
            overall_confidence=overall_confidence,
            adherence_rate=adherence_rate,
            confounders_json=confounders,
            evaluation_ids_json=evaluation_ids,
        )

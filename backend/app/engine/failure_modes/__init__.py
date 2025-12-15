"""Failure modes and safe degradation handling."""

from app.engine.failure_modes.degradation import (
    DegradationState,
    check_insufficient_data,
    check_conflicting_signals,
    check_data_quality_drop,
    check_human_review_needed,
    freeze_baselines_if_disconnected,
    mark_evaluation_unreliable,
    suppress_intervention_for_swings,
    invalidate_protocol_on_safety_change,
)

__all__ = [
    "DegradationState",
    "check_insufficient_data",
    "check_conflicting_signals",
    "check_data_quality_drop",
    "check_human_review_needed",
    "freeze_baselines_if_disconnected",
    "mark_evaluation_unreliable",
    "suppress_intervention_for_swings",
    "invalidate_protocol_on_safety_change",
]


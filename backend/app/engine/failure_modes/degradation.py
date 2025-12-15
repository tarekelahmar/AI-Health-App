"""
X5: Failure Modes & Safe Degradation

Explicit handling for bad situations:
- "Insufficient data" states
- "Conflicting signals" resolution
- "Paused learning" when data quality drops
- "Human review recommended" triggers
- Freeze baselines if wearables disconnect
- Mark evaluations unreliable if adherence is low
- Suppress interventions for rapid metric swings
- Invalidate protocols on safety flag changes
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, date
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple

from sqlalchemy.orm import Session

from app.domain.models.baseline import Baseline
from app.domain.models.health_data_point import HealthDataPoint
from app.domain.models.evaluation_result import EvaluationResult
from app.domain.models.intervention import Intervention
from app.domain.models.protocol import Protocol
from app.domain.repositories.health_data_repository import HealthDataRepository

logger = logging.getLogger(__name__)


class DegradationState(str, Enum):
    """State of system degradation."""
    NORMAL = "normal"
    INSUFFICIENT_DATA = "insufficient_data"
    CONFLICTING_SIGNALS = "conflicting_signals"
    PAUSED_LEARNING = "paused_learning"
    HUMAN_REVIEW_NEEDED = "human_review_needed"
    BASELINES_FROZEN = "baselines_frozen"
    EVALUATION_UNRELIABLE = "evaluation_unreliable"
    INTERVENTION_SUPPRESSED = "intervention_suppressed"
    PROTOCOL_INVALIDATED = "protocol_invalidated"


@dataclass
class DegradationResult:
    """Result of degradation check."""
    state: DegradationState
    reason: str
    metadata: Dict[str, Any]
    should_block: bool = False  # If True, block the operation
    should_warn: bool = True  # If True, log a warning


def check_insufficient_data(
    db: Session,
    user_id: int,
    metric_key: str,
    min_data_points: int = 7,
    window_days: int = 14,
) -> Optional[DegradationResult]:
    """
    Check if there's insufficient data for a metric.
    
    Returns DegradationResult if insufficient, None otherwise.
    """
    repo = HealthDataRepository(db)
    
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=window_days)
    
    points = repo.get_by_time_range(
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        data_type=metric_key,
    )
    
    if len(points) < min_data_points:
        return DegradationResult(
            state=DegradationState.INSUFFICIENT_DATA,
            reason=f"Insufficient data points for {metric_key}: {len(points)} < {min_data_points}",
            metadata={
                "metric_key": metric_key,
                "data_points": len(points),
                "min_required": min_data_points,
                "window_days": window_days,
            },
            should_block=False,  # Don't block, but warn
            should_warn=True,
        )
    
    return None


def check_conflicting_signals(
    db: Session,
    user_id: int,
    metric_key: str,
    window_days: int = 7,
) -> Optional[DegradationResult]:
    """
    Check for conflicting signals (e.g., wearable says one thing, subjective says another).
    
    Returns DegradationResult if conflicts detected, None otherwise.
    """
    repo = HealthDataRepository(db)
    
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=window_days)
    
    # Get data from different sources
    wearable_points = repo.list_by_metric_and_range(
        user_id=user_id,
        metric_type=metric_key,
        start_date=start_date,
        end_date=end_date,
    )
    wearable_points = [p for p in wearable_points if p.source == "wearable"]
    
    subjective_points = repo.list_by_metric_and_range(
        user_id=user_id,
        metric_type=metric_key,
        start_date=start_date,
        end_date=end_date,
    )
    subjective_points = [p for p in subjective_points if p.source == "subjective"]
    
    if len(wearable_points) == 0 or len(subjective_points) == 0:
        return None  # No conflict if one source is missing
    
    # Compute means
    wearable_mean = sum(p.value for p in wearable_points) / len(wearable_points)
    subjective_mean = sum(p.value for p in subjective_points) / len(subjective_points)
    
    # Check if means differ significantly (more than 20% relative difference)
    if wearable_mean > 0:
        relative_diff = abs(wearable_mean - subjective_mean) / wearable_mean
        if relative_diff > 0.2:  # 20% difference
            return DegradationResult(
                state=DegradationState.CONFLICTING_SIGNALS,
                reason=f"Conflicting signals for {metric_key}: wearable={wearable_mean:.2f}, subjective={subjective_mean:.2f}",
                metadata={
                    "metric_key": metric_key,
                    "wearable_mean": wearable_mean,
                    "subjective_mean": subjective_mean,
                    "relative_diff": relative_diff,
                },
                should_block=False,
                should_warn=True,
            )
    
    return None


def check_data_quality_drop(
    db: Session,
    user_id: int,
    metric_key: str,
    quality_threshold: float = 0.6,
    window_days: int = 7,
) -> Optional[DegradationResult]:
    """
    Check if data quality has dropped below threshold.
    
    Returns DegradationResult if quality dropped, None otherwise.
    """
    repo = HealthDataRepository(db)
    
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=window_days)
    
    points = repo.get_by_time_range(
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        data_type=metric_key,
    )
    
    if len(points) == 0:
        return None
    
    # Check quality scores (if available)
    quality_scores = []
    for p in points:
        if hasattr(p, "quality_score") and p.quality_score:
            if isinstance(p.quality_score, dict):
                quality_scores.append(p.quality_score.get("overall", 1.0))
            elif isinstance(p.quality_score, (int, float)):
                quality_scores.append(float(p.quality_score))
    
    if len(quality_scores) == 0:
        return None  # No quality scores available
    
    avg_quality = sum(quality_scores) / len(quality_scores)
    
    if avg_quality < quality_threshold:
        return DegradationResult(
            state=DegradationState.PAUSED_LEARNING,
            reason=f"Data quality dropped for {metric_key}: {avg_quality:.2f} < {quality_threshold}",
            metadata={
                "metric_key": metric_key,
                "avg_quality": avg_quality,
                "threshold": quality_threshold,
                "n_points": len(quality_scores),
            },
            should_block=False,  # Pause learning but don't block
            should_warn=True,
        )
    
    return None


def check_human_review_needed(
    *,
    confidence: float,
    safety_risk_level: Optional[str] = None,
    effect_size: Optional[float] = None,
) -> Optional[DegradationResult]:
    """
    Check if human review is needed based on confidence, safety, or effect size.
    
    Returns DegradationResult if review needed, None otherwise.
    """
    triggers = []
    
    if confidence < 0.3:
        triggers.append("low_confidence")
    
    if safety_risk_level == "high":
        triggers.append("high_safety_risk")
    
    if effect_size and abs(effect_size) > 2.0:  # Very large effect
        triggers.append("large_effect_size")
    
    if triggers:
        return DegradationResult(
            state=DegradationState.HUMAN_REVIEW_NEEDED,
            reason=f"Human review recommended: {', '.join(triggers)}",
            metadata={
                "triggers": triggers,
                "confidence": confidence,
                "safety_risk_level": safety_risk_level,
                "effect_size": effect_size,
            },
            should_block=False,
            should_warn=True,
        )
    
    return None


def freeze_baselines_if_disconnected(
    db: Session,
    user_id: int,
    metric_key: str,
    disconnect_threshold_hours: int = 48,
) -> Optional[DegradationResult]:
    """
    Freeze baselines if wearable data hasn't been received recently.
    
    Returns DegradationResult if baselines should be frozen, None otherwise.
    """
    repo = HealthDataRepository(db)
    
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(hours=disconnect_threshold_hours)
    
    recent_points = repo.list_by_metric_and_range(
        user_id=user_id,
        metric_type=metric_key,
        start_date=start_date,
        end_date=end_date,
    )
    recent_points = [p for p in recent_points if p.source == "wearable"]
    
    if len(recent_points) == 0:
        # Check if baseline exists
        baseline = (
            db.query(Baseline)
            .filter(Baseline.user_id == user_id, Baseline.metric_type == metric_key)
            .first()
        )
        
        if baseline:
            return DegradationResult(
                state=DegradationState.BASELINES_FROZEN,
                reason=f"Wearable disconnected for {metric_key}, baselines frozen",
                metadata={
                    "metric_key": metric_key,
                    "last_data_point": None,
                    "disconnect_threshold_hours": disconnect_threshold_hours,
                },
                should_block=False,
                should_warn=True,
            )
    
    return None


def mark_evaluation_unreliable(
    evaluation: EvaluationResult,
    min_adherence_rate: float = 0.7,
) -> Optional[DegradationResult]:
    """
    Mark evaluation as unreliable if adherence is too low.
    
    Returns DegradationResult if unreliable, None otherwise.
    """
    if evaluation.adherence_rate < min_adherence_rate:
        return DegradationResult(
            state=DegradationState.EVALUATION_UNRELIABLE,
            reason=f"Evaluation unreliable due to low adherence: {evaluation.adherence_rate:.2f} < {min_adherence_rate}",
            metadata={
                "evaluation_id": evaluation.id,
                "adherence_rate": evaluation.adherence_rate,
                "min_required": min_adherence_rate,
            },
            should_block=False,
            should_warn=True,
        )
    
    return None


def suppress_intervention_for_swings(
    db: Session,
    user_id: int,
    metric_key: str,
    swing_threshold_std: float = 2.0,
    window_days: int = 3,
) -> Optional[DegradationResult]:
    """
    Suppress interventions if metric is swinging rapidly.
    
    Returns DegradationResult if intervention should be suppressed, None otherwise.
    """
    repo = HealthDataRepository(db)
    
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=window_days)
    
    points = repo.get_by_time_range(
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        data_type=metric_key,
    )
    
    if len(points) < 3:
        return None  # Not enough data to detect swings
    
    values = [p.value for p in points]
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    std = variance ** 0.5
    
    # Get baseline std for comparison
    baseline = (
        db.query(Baseline)
        .filter(Baseline.user_id == user_id, Baseline.metric_type == metric_key)
        .first()
    )
    
    if baseline and baseline.std > 0:
        # Check if recent std is much higher than baseline
        if std > baseline.std * swing_threshold_std:
            return DegradationResult(
                state=DegradationState.INTERVENTION_SUPPRESSED,
                reason=f"Intervention suppressed due to rapid swings in {metric_key}: std={std:.2f} > {baseline.std * swing_threshold_std:.2f}",
                metadata={
                    "metric_key": metric_key,
                    "recent_std": std,
                    "baseline_std": baseline.std,
                    "swing_threshold": swing_threshold_std,
                },
                should_block=True,  # Block intervention
                should_warn=True,
            )
    
    return None


def invalidate_protocol_on_safety_change(
    protocol: Protocol,
    previous_safety_flags: Dict[str, Any],
    current_safety_flags: Dict[str, Any],
) -> Optional[DegradationResult]:
    """
    Invalidate protocol if safety flags have changed significantly.
    
    Returns DegradationResult if protocol should be invalidated, None otherwise.
    """
    # Check if risk level increased
    prev_risk = previous_safety_flags.get("risk_level", "low")
    curr_risk = current_safety_flags.get("risk_level", "low")
    
    risk_levels = {"low": 0, "moderate": 1, "high": 2}
    prev_level = risk_levels.get(prev_risk, 0)
    curr_level = risk_levels.get(curr_risk, 0)
    
    if curr_level > prev_level:
        return DegradationResult(
            state=DegradationState.PROTOCOL_INVALIDATED,
            reason=f"Protocol invalidated due to safety risk increase: {prev_risk} -> {curr_risk}",
            metadata={
                "protocol_id": protocol.id,
                "previous_risk": prev_risk,
                "current_risk": curr_risk,
            },
            should_block=True,  # Block protocol use
            should_warn=True,
        )
    
    return None


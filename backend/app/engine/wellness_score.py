"""
Wellness score computation engine.

Computes a composite 0-100 wellness score by:
1. Gathering today's objective (wearable) and subjective (journal) signals
2. Computing z-scores against personal baselines
3. Weighted combination: 60% objective / 40% subjective (when both present)
4. Mapping composite z-score to 0-100 scale

Score interpretation:
  z=0 (at baseline) -> 70  ("normal is good")
  z=+2 (excellent)  -> 95
  z=-2 (poor)       -> 45
  Clamped to [5, 99]
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScoreContributingFactor:
    """A signal contributing to the wellness score."""
    metric_key: str
    label: str
    z_score: float
    weight: float
    direction: str  # "positive" (helping) or "negative" (hurting)
    category: str  # "objective" or "subjective"


@dataclass
class WellnessScoreResult:
    """Result of a wellness score computation."""
    score: float  # 0-100
    objective_score: Optional[float]  # 0-100 or None if no objective data
    subjective_score: Optional[float]  # 0-100 or None if no subjective data
    contributing_factors: List[ScoreContributingFactor] = field(default_factory=list)
    composite_z: float = 0.0


# Signal definitions: metric_key -> (weight, higher_is_better, display_label)
OBJECTIVE_SIGNALS: Dict[str, Tuple[float, bool, str]] = {
    "hrv_rmssd": (0.30, True, "HRV"),
    "sleep_duration": (0.25, True, "Sleep Duration"),
    "resting_hr": (0.20, False, "Resting HR"),
    "sleep_efficiency": (0.15, True, "Sleep Efficiency"),
    "hrv": (0.00, True, "HRV (alias)"),  # Only used if hrv_rmssd absent
}

SUBJECTIVE_SIGNALS: Dict[str, Tuple[float, bool, str]] = {
    "energy": (0.25, True, "Energy"),
    "mood": (0.25, True, "Mood"),
    "sleep_quality": (0.20, True, "Sleep Quality"),
    "stress": (0.20, False, "Stress"),
    "focus": (0.10, True, "Focus"),
}

# Weighting between objective and subjective
OBJECTIVE_WEIGHT = 0.60
SUBJECTIVE_WEIGHT = 0.40

# Score mapping parameters
BASELINE_SCORE = 70.0  # z=0 maps to this
Z_SCALE = 12.5  # score points per z-score unit
SCORE_MIN = 5.0
SCORE_MAX = 99.0


def _z_to_score(z: float) -> float:
    """Map a z-score to a 0-100 wellness score."""
    score = BASELINE_SCORE + z * Z_SCALE
    return max(SCORE_MIN, min(SCORE_MAX, score))


def _compute_category_z(
    signal_defs: Dict[str, Tuple[float, bool, str]],
    values: Dict[str, float],
    baselines: Dict[str, Tuple[float, float]],
    category: str,
) -> Tuple[Optional[float], List[ScoreContributingFactor]]:
    """
    Compute weighted z-score for a category of signals.

    Returns (composite_z, list_of_factors) or (None, []) if no data.
    """
    weighted_z_sum = 0.0
    total_weight = 0.0
    factors = []

    for metric_key, (weight, higher_is_better, label) in signal_defs.items():
        if weight == 0.0:
            continue

        value = values.get(metric_key)
        baseline = baselines.get(metric_key)

        if value is None or baseline is None:
            continue

        center, spread = baseline
        if spread < 1e-10:
            spread = 0.1  # Prevent division by zero

        z = (value - center) / spread

        # Flip sign for "lower is better" metrics so positive z = good
        if not higher_is_better:
            z = -z

        weighted_z_sum += z * weight
        total_weight += weight

        factors.append(ScoreContributingFactor(
            metric_key=metric_key,
            label=label,
            z_score=round(z, 2),
            weight=weight,
            direction="positive" if z >= 0 else "negative",
            category=category,
        ))

    if total_weight == 0:
        return None, []

    composite_z = weighted_z_sum / total_weight
    return composite_z, factors


def compute_wellness_score(
    objective_values: Dict[str, float],
    subjective_values: Dict[str, float],
    baselines: Dict[str, Tuple[float, float]],
) -> WellnessScoreResult:
    """
    Compute composite wellness score from objective + subjective data.

    Args:
        objective_values: metric_key -> current value (wearable data)
        subjective_values: metric_key -> current value (journal data, already on 1-5 scale)
        baselines: metric_key -> (center, spread) from Baseline model

    Returns:
        WellnessScoreResult with composite score and breakdown
    """
    obj_z, obj_factors = _compute_category_z(
        OBJECTIVE_SIGNALS, objective_values, baselines, "objective"
    )
    subj_z, subj_factors = _compute_category_z(
        SUBJECTIVE_SIGNALS, subjective_values, baselines, "subjective"
    )

    all_factors = obj_factors + subj_factors

    # Compute composite z-score with dynamic weighting
    if obj_z is not None and subj_z is not None:
        composite_z = obj_z * OBJECTIVE_WEIGHT + subj_z * SUBJECTIVE_WEIGHT
    elif obj_z is not None:
        composite_z = obj_z
    elif subj_z is not None:
        composite_z = subj_z
    else:
        # No data at all
        return WellnessScoreResult(
            score=BASELINE_SCORE,
            objective_score=None,
            subjective_score=None,
            contributing_factors=[],
            composite_z=0.0,
        )

    score = _z_to_score(composite_z)
    obj_score = _z_to_score(obj_z) if obj_z is not None else None
    subj_score = _z_to_score(subj_z) if subj_z is not None else None

    # Sort factors: most impactful first (by absolute z * weight)
    all_factors.sort(key=lambda f: abs(f.z_score * f.weight), reverse=True)

    return WellnessScoreResult(
        score=round(score, 1),
        objective_score=round(obj_score, 1) if obj_score is not None else None,
        subjective_score=round(subj_score, 1) if subj_score is not None else None,
        contributing_factors=all_factors,
        composite_z=round(composite_z, 3),
    )

from math import exp
from typing import Optional


def compute_confidence(
    *,
    sample_days: int,
    expected_days: int,
    effect_size: Optional[float],
    consistency_ratio: float,
) -> float:
    """
    Returns confidence in [0, 1]
    """

    coverage = min(sample_days / expected_days, 1.0)

    effect_component = 0.5
    if effect_size is not None:
        # squash effect size into 0..1
        effect_component = 1 - exp(-abs(effect_size))

    confidence = 0.4 * coverage + 0.4 * effect_component + 0.2 * consistency_ratio

    return max(0.0, min(1.0, confidence))


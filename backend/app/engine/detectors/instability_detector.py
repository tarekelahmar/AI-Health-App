from dataclasses import dataclass
from typing import Optional
from statistics import pstdev


@dataclass
class InstabilityResult:
    metric_key: str
    recent_std: float
    baseline_std: float
    ratio: float
    n_points: int
    window_days: int
    strength: str  # "moderate" | "strong"


def detect_instability(
    *,
    metric_key: str,
    values: list[float],
    baseline_std: float,
    window_days: int,
    ratio_threshold: float,
    min_points: int = 7,
) -> Optional[InstabilityResult]:
    if len(values) < min_points:
        return None
    if baseline_std <= 0.00001:
        return None

    recent_std = pstdev(values) if len(values) > 1 else 0.0
    ratio = recent_std / baseline_std

    # Use metric-specific threshold
    if ratio < ratio_threshold:
        return None

    strength = "strong" if ratio >= 2.5 else "moderate"

    return InstabilityResult(
        metric_key=metric_key,
        recent_std=recent_std,
        baseline_std=baseline_std,
        ratio=ratio,
        n_points=len(values),
        window_days=window_days,
        strength=strength,
    )


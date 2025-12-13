from dataclasses import dataclass
from typing import Optional


@dataclass
class ChangeResult:
    metric_key: str
    z_score: float
    recent_mean: float
    baseline_mean: float
    baseline_std: float
    n_points: int
    window_days: int
    direction: str  # "up" or "down"
    strength: str   # "weak" | "moderate" | "strong"


def detect_change(
    *,
    metric_key: str,
    values: list[float],
    baseline_mean: float,
    baseline_std: float,
    window_days: int,
    z_threshold: float,
) -> Optional[ChangeResult]:
    if len(values) < 5:
        return None
    if baseline_std <= 0.00001:
        return None

    recent_mean = sum(values) / len(values)
    z = (recent_mean - baseline_mean) / baseline_std

    direction = "up" if z > 0 else "down"
    absz = abs(z)

    if absz >= 2.5:
        strength = "strong"
    elif absz >= 1.5:
        strength = "moderate"
    else:
        strength = "weak"

    # Only return meaningful changes (use metric-specific threshold)
    if absz < z_threshold:
        return None

    return ChangeResult(
        metric_key=metric_key,
        z_score=z,
        recent_mean=recent_mean,
        baseline_mean=baseline_mean,
        baseline_std=baseline_std,
        n_points=len(values),
        window_days=window_days,
        direction=direction,
        strength=strength,
    )


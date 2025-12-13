from dataclasses import dataclass
from typing import Optional


@dataclass
class TrendResult:
    metric_key: str
    slope_per_day: float
    n_points: int
    window_days: int
    direction: str  # "up" or "down"
    strength: str   # "weak" | "moderate" | "strong"


def _linear_regression_slope(y: list[float]) -> float:
    # x = 0..n-1
    n = len(y)
    xs = list(range(n))
    x_mean = sum(xs) / n
    y_mean = sum(y) / n

    num = sum((xs[i] - x_mean) * (y[i] - y_mean) for i in range(n))
    den = sum((xs[i] - x_mean) ** 2 for i in range(n))
    if den == 0:
        return 0.0
    return num / den


def detect_trend(
    *,
    metric_key: str,
    values: list[float],
    window_days: int,
    slope_threshold: float,
    min_points: int = 7,
) -> Optional[TrendResult]:
    if len(values) < min_points:
        return None

    slope = _linear_regression_slope(values)

    direction = "up" if slope > 0 else "down"
    abs_slope = abs(slope)

    # Generic thresholds; can be tuned per metric later
    if abs_slope >= 1.0:
        strength = "strong"
    elif abs_slope >= 0.3:
        strength = "moderate"
    else:
        strength = "weak"

    # Use metric-specific threshold
    if abs_slope < slope_threshold:
        return None

    return TrendResult(
        metric_key=metric_key,
        slope_per_day=slope,
        n_points=len(values),
        window_days=window_days,
        direction=direction,
        strength=strength,
    )


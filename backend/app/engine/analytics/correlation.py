"""Correlation analysis between health metrics.

Given two aligned daily time series, compute basic Pearson correlation and
a qualitative interpretation (weak / moderate / strong).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Dict, Any, Optional, Tuple

from .time_series import DailyMetric


@dataclass
class CorrelationResult:
    metric_x: str
    metric_y: str
    r: float
    n: int
    strength: str
    direction: str
    is_reliable: bool


def _align_series_by_date(
    series_x: Sequence[DailyMetric],
    series_y: Sequence[DailyMetric],
) -> Tuple[list[float], list[float]]:
    """Align two daily series by date, returning paired values."""
    map_x = {item.date: item.value for item in series_x}
    map_y = {item.date: item.value for item in series_y}

    common_dates = sorted(set(map_x.keys()) & set(map_y.keys()))
    xs = [map_x[d] for d in common_dates]
    ys = [map_y[d] for d in common_dates]

    return xs, ys


def _pearson_correlation(xs: Sequence[float], ys: Sequence[float]) -> Optional[float]:
    """Compute Pearson correlation coefficient r between two sequences."""
    n = len(xs)
    if n < 2:
        return None

    mean_x = sum(xs) / n
    mean_y = sum(ys) / n

    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den_x = sum((x - mean_x) ** 2 for x in xs)
    den_y = sum((y - mean_y) ** 2 for y in ys)

    if den_x <= 0 or den_y <= 0:
        return None

    r = num / (den_x * den_y) ** 0.5
    return max(min(r, 1.0), -1.0)  # clamp in case of float noise


def _interpret_strength(r: float, n: int) -> str:
    """Rough qualitative interpretation of correlation strength."""
    ar = abs(r)

    if n < 10:
        # with very few points, downplay strength
        if ar >= 0.7:
            return "moderate (low data)"
        elif ar >= 0.4:
            return "weak (low data)"
        else:
            return "none (low data)"

    if ar >= 0.7:
        return "strong"
    elif ar >= 0.5:
        return "moderate"
    elif ar >= 0.3:
        return "weak"
    else:
        return "none"


def _is_reliable(r: float, n: int) -> bool:
    """Basic reliability heuristic."""
    return n >= 10 and abs(r) >= 0.3


def compute_metric_correlation(
    metric_x_name: str,
    metric_y_name: str,
    series_x: Sequence[DailyMetric],
    series_y: Sequence[DailyMetric],
) -> Optional[CorrelationResult]:
    """
    Compute correlation between two metrics, given their daily series.

    Returns None if there is insufficient overlapping data.
    """
    xs, ys = _align_series_by_date(series_x, series_y)
    n = len(xs)

    if n < 3:
        return None

    r = _pearson_correlation(xs, ys)
    if r is None:
        return None

    strength = _interpret_strength(r, n)
    direction = "positive" if r > 0 else "negative" if r < 0 else "none"
    reliable = _is_reliable(r, n)

    return CorrelationResult(
        metric_x=metric_x_name,
        metric_y=metric_y_name,
        r=r,
        n=n,
        strength=strength,
        direction=direction,
        is_reliable=reliable,
    )


def to_dict(result: CorrelationResult) -> Dict[str, Any]:
    """Convert CorrelationResult into a JSON-serialisable dict."""
    return {
        "metric_x": result.metric_x,
        "metric_y": result.metric_y,
        "r": result.r,
        "n": result.n,
        "strength": result.strength,
        "direction": result.direction,
        "is_reliable": result.is_reliable,
    }

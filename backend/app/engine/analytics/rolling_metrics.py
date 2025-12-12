"""Rolling window metrics for health time series.

Given a daily time series, compute rolling statistics like mean, std, min, max.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import List, Dict, Sequence

from .time_series import DailyMetric


@dataclass
class RollingStat:
    date: str  # ISO string for easier serialisation
    mean: float
    std: float
    minimum: float
    maximum: float
    count: int


def _compute_basic_stats(values: Sequence[float]) -> Dict[str, float]:
    n = len(values)
    if n == 0:
        return {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0}

    mean = sum(values) / n

    if n > 1:
        var = sum((v - mean) ** 2 for v in values) / (n - 1)
        std = sqrt(max(var, 0.0))
    else:
        std = 0.0

    return {
        "mean": mean,
        "std": std,
        "min": min(values),
        "max": max(values),
    }


def compute_rolling_stats(
    series: Sequence[DailyMetric],
    window_size: int = 7,
) -> List[RollingStat]:
    """
    Compute rolling window stats over a daily series.

    window_size: how many *data points* (days with data) to include in each window.
    """
    if window_size <= 0:
        raise ValueError("window_size must be > 0")

    if not series:
        return []

    # ensure sorted by date
    sorted_series = sorted(series, key=lambda x: x.date)
    values = [item.value for item in sorted_series]

    results: List[RollingStat] = []

    for i in range(len(sorted_series)):
        window_start = max(0, i - window_size + 1)
        window_values = values[window_start : i + 1]

        stats = _compute_basic_stats(window_values)

        results.append(
            RollingStat(
                date=sorted_series[i].date.isoformat(),
                mean=stats["mean"],
                std=stats["std"],
                minimum=stats["min"],
                maximum=stats["max"],
                count=len(window_values),
            )
        )

    return results


def to_dict_series(stats: Sequence[RollingStat]) -> List[Dict[str, float]]:
    """Convert RollingStat objects to plain dicts for JSON / LLM consumption."""
    return [
        {
            "date": s.date,
            "mean": s.mean,
            "std": s.std,
            "min": s.minimum,
            "max": s.maximum,
            "count": s.count,
        }
        for s in stats
    ]

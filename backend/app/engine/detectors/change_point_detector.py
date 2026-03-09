"""
Change point detection using PELT (Pruned Exact Linear Time).

Phase 2.3: Detects sudden regime shifts in time series data.
Unlike the rolling-window z-score detector, this finds the exact
points where the underlying distribution changes.

Use cases:
- Detecting when a user gets sick (sudden HR increase, HRV drop)
- Detecting when a supplement starts working
- Detecting lifestyle changes (new job, moved, etc.)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

import numpy as np
import ruptures as rpt


@dataclass(frozen=True)
class ChangePoint:
    """A detected change point in a time series."""
    index: int  # Position in the series
    timestamp: Optional[datetime]  # If timestamps provided
    magnitude: float  # Size of the shift (difference of segment means)
    direction: str  # "increase" or "decrease"
    confidence: float  # 0-1 based on segment statistics
    before_mean: float
    after_mean: float
    before_std: float
    after_std: float


@dataclass(frozen=True)
class ChangePointResult:
    """Result of change point detection on a metric."""
    metric_key: str
    change_points: List[ChangePoint]
    n_segments: int
    method: str


def detect_change_points(
    *,
    metric_key: str,
    values: list[float],
    timestamps: Optional[list[datetime]] = None,
    method: str = "pelt",
    min_segment_size: int = 7,
    penalty: Optional[float] = None,
) -> Optional[ChangePointResult]:
    """
    Detect change points in a time series using PELT or other methods.

    Args:
        metric_key: The metric being analyzed
        values: Ordered time series values
        timestamps: Optional timestamps for each value
        method: Detection method ("pelt" or "binseg")
        min_segment_size: Minimum segment length (days)
        penalty: PELT penalty parameter (auto-computed if None)

    Returns:
        ChangePointResult with detected change points, or None if
        insufficient data.
    """
    if len(values) < min_segment_size * 2:
        return None

    arr = np.array(values, dtype=np.float64)

    # Auto-compute penalty if not specified
    # Use a scaled log-penalty that works well for health metrics
    # Lower penalty = more sensitive to changes
    if penalty is None:
        n = len(arr)
        # Standard BIC-like penalty scaled by number of observations
        # Using 2 * log(n) provides good balance between sensitivity and specificity
        penalty = 2.0 * np.log(n)
        penalty = max(penalty, 1.0)

    if method == "pelt":
        algo = rpt.Pelt(model="rbf", min_size=min_segment_size)
    elif method == "binseg":
        algo = rpt.Binseg(model="rbf", min_size=min_segment_size)
    else:
        raise ValueError(f"Unknown change point method: {method}")

    try:
        breakpoints = algo.fit_predict(arr, pen=penalty)
    except Exception:
        return ChangePointResult(
            metric_key=metric_key,
            change_points=[],
            n_segments=1,
            method=method,
        )

    # ruptures returns indices where segments end (last element is always len(arr))
    # Convert to change point objects
    change_points = []
    segment_starts = [0] + breakpoints[:-1]  # Start indices
    segment_ends = breakpoints  # End indices

    for i in range(len(segment_starts) - 1):
        cp_idx = segment_ends[i]
        before_segment = arr[segment_starts[i]:cp_idx]
        after_segment = arr[cp_idx:segment_ends[i + 1]]

        if len(before_segment) < 2 or len(after_segment) < 2:
            continue

        before_mean = float(np.mean(before_segment))
        after_mean = float(np.mean(after_segment))
        before_std = float(np.std(before_segment, ddof=1))
        after_std = float(np.std(after_segment, ddof=1))

        magnitude = after_mean - before_mean
        direction = "increase" if magnitude > 0 else "decrease"

        # Confidence based on effect size relative to pooled std
        pooled_std = np.sqrt(
            ((len(before_segment) - 1) * before_std**2 +
             (len(after_segment) - 1) * after_std**2) /
            (len(before_segment) + len(after_segment) - 2)
        )
        if pooled_std > 1e-10:
            effect_size = abs(magnitude) / pooled_std
            confidence = min(1.0, effect_size / 3.0)  # Scale: d=3 → full confidence
        else:
            confidence = 1.0 if abs(magnitude) > 1e-10 else 0.0

        ts = timestamps[cp_idx] if timestamps and cp_idx < len(timestamps) else None

        change_points.append(ChangePoint(
            index=cp_idx,
            timestamp=ts,
            magnitude=abs(magnitude),
            direction=direction,
            confidence=round(confidence, 3),
            before_mean=round(before_mean, 3),
            after_mean=round(after_mean, 3),
            before_std=round(before_std, 3),
            after_std=round(after_std, 3),
        ))

    return ChangePointResult(
        metric_key=metric_key,
        change_points=change_points,
        n_segments=len(breakpoints),
        method=method,
    )

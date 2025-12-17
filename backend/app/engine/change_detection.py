from datetime import datetime, timedelta
from typing import List, Optional

from app.core.signal import Signal
from app.engine.baselines import Baseline
# AUDIT FIX: Use single metric registry
from app.domain.metric_registry import METRICS as CANONICAL_METRICS


class ChangeEvent:
    def __init__(
        self,
        metric_key: str,
        direction: str,   # "increase" or "decrease"
        severity: float,  # how many std devs
        days_consistent: int,
    ):
        self.metric_key = metric_key
        self.direction = direction
        self.severity = severity
        self.days_consistent = days_consistent


def detect_change(
    *,
    signals: List[Signal],
    baseline: Baseline,
    now: datetime,
    lookback_days: int = 5,
    min_consistent_days: int = 3,
    threshold_std: float = 1.5,
) -> Optional[ChangeEvent]:

    metric = CANONICAL_METRICS[baseline.metric_key]
    window_start = now - timedelta(days=lookback_days)

    recent_values = [
        s.value
        for s in signals
        if s.metric_key == baseline.metric_key
        and s.timestamp >= window_start
    ]

    if len(recent_values) < min_consistent_days:
        return None

    deviations = [
        (v - baseline.mean) / baseline.std
        if baseline.std > 0
        else 0.0
        for v in recent_values
    ]

    significant = [
        d for d in deviations if abs(d) >= threshold_std
    ]

    if len(significant) < min_consistent_days:
        return None

    avg_dev = sum(significant) / len(significant)
    direction = "increase" if avg_dev > 0 else "decrease"

    return ChangeEvent(
        metric_key=baseline.metric_key,
        direction=direction,
        severity=abs(avg_dev),
        days_consistent=len(significant),
    )


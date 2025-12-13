from typing import List, Dict, Optional
from statistics import mean, stdev
from datetime import datetime, timedelta

from app.core.signal import Signal


class Baseline:
    def __init__(
        self,
        metric_key: str,
        mean_value: float,
        std_value: float,
        sample_count: int,
        window_days: int,
    ):
        self.metric_key = metric_key
        self.mean = mean_value
        self.std = std_value
        self.sample_count = sample_count
        self.window_days = window_days


def compute_baseline(
    signals: List[Signal],
    metric_key: str,
    now: datetime,
    window_days: int = 30,
    min_samples: int = 7,
) -> Optional[Baseline]:
    """
    Compute personal baseline for one metric.
    """

    window_start = now - timedelta(days=window_days)

    values = [
        s.value
        for s in signals
        if s.metric_key == metric_key and s.timestamp >= window_start
    ]

    if len(values) < min_samples:
        return None

    if len(values) == 1:
        return Baseline(
            metric_key=metric_key,
            mean_value=values[0],
            std_value=0.0,
            sample_count=1,
            window_days=window_days,
        )

    return Baseline(
        metric_key=metric_key,
        mean_value=mean(values),
        std_value=stdev(values),
        sample_count=len(values),
        window_days=window_days,
    )


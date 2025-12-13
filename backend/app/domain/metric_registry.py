from dataclasses import dataclass
from typing import Optional, Dict


@dataclass(frozen=True)
class MetricSpec:
    key: str
    unit: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    description: str = ""


# MVP Observe Set (expand later)
METRICS: Dict[str, MetricSpec] = {
    # Wearables (objective)
    "sleep_duration": MetricSpec("sleep_duration", "minutes", 0, 1000, "Total sleep duration"),
    "sleep_efficiency": MetricSpec("sleep_efficiency", "percent", 0, 100, "Sleep efficiency %"),
    "resting_hr": MetricSpec("resting_hr", "bpm", 20, 200, "Resting heart rate"),
    "hrv_rmssd": MetricSpec("hrv_rmssd", "ms", 0, 300, "HRV RMSSD"),
    "steps": MetricSpec("steps", "count", 0, 100000, "Daily steps"),

    # Subjective (user input)
    "sleep_quality": MetricSpec("sleep_quality", "score_1_5", 1, 5, "Self-reported sleep quality"),
    "energy": MetricSpec("energy", "score_1_5", 1, 5, "Self-reported energy"),
    "stress": MetricSpec("stress", "score_1_5", 1, 5, "Self-reported stress"),
}


def get_metric_spec(metric_key: str) -> MetricSpec:
    if metric_key not in METRICS:
        raise ValueError(f"Unknown metric_key: {metric_key}")
    return METRICS[metric_key]


from dataclasses import dataclass
from typing import Optional, Dict, List, Literal
from enum import Enum


class MetricDirection(str, Enum):
    """Whether higher values are better or worse."""
    HIGHER_IS_BETTER = "higher_is_better"
    LOWER_IS_BETTER = "lower_is_better"
    NEUTRAL = "neutral"


class MetricAggregation(str, Enum):
    """How to aggregate multiple values per day."""
    MEAN = "mean"  # Average (e.g., resting HR)
    SUM = "sum"    # Sum (e.g., steps, sleep duration)
    LAST = "last"  # Last value (e.g., weight)
    MAX = "max"    # Maximum (e.g., peak HR)
    MIN = "min"    # Minimum (e.g., lowest HR)


@dataclass(frozen=True)
class MetricSpec:
    """
    SECURITY FIX (Risk #6): Expanded metric specification.
    
    Includes:
    - directionality: whether higher is better/worse
    - aggregation: how to aggregate multiple values
    - expected_cadence: how often values are expected
    - valid_units: list of acceptable units (for validation)
    """
    key: str
    unit: str  # Canonical unit
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    description: str = ""
    direction: MetricDirection = MetricDirection.NEUTRAL
    aggregation: MetricAggregation = MetricAggregation.MEAN
    expected_cadence: str = "daily"  # "daily", "hourly", "weekly", "on_demand"
    valid_units: Optional[List[str]] = None  # If None, only canonical unit is valid


# MVP Observe Set (expand later)
# SECURITY FIX (Risk #6): Expanded with directionality, aggregation, valid units
METRICS: Dict[str, MetricSpec] = {
    # Wearables (objective)
    "sleep_duration": MetricSpec(
        key="sleep_duration",
        unit="minutes",
        min_value=0,
        max_value=1000,
        description="Total sleep duration",
        direction=MetricDirection.HIGHER_IS_BETTER,
        aggregation=MetricAggregation.SUM,
        expected_cadence="daily",
        valid_units=["minutes", "min", "hours", "hr", "hrs", "h"],  # Allow hours, convert to minutes
    ),
    "sleep_efficiency": MetricSpec(
        key="sleep_efficiency",
        unit="percent",
        min_value=0,
        max_value=100,
        description="Sleep efficiency %",
        direction=MetricDirection.HIGHER_IS_BETTER,
        aggregation=MetricAggregation.MEAN,
        expected_cadence="daily",
        valid_units=["percent", "%", "ratio", "decimal"],
    ),
    "resting_hr": MetricSpec(
        key="resting_hr",
        unit="bpm",
        min_value=20,
        max_value=200,
        description="Resting heart rate",
        direction=MetricDirection.LOWER_IS_BETTER,
        aggregation=MetricAggregation.MEAN,
        expected_cadence="daily",
        valid_units=["bpm", "beats_per_minute"],
    ),
    "hrv_rmssd": MetricSpec(
        key="hrv_rmssd",
        unit="ms",
        min_value=0,
        max_value=300,
        description="HRV RMSSD",
        direction=MetricDirection.HIGHER_IS_BETTER,
        aggregation=MetricAggregation.MEAN,
        expected_cadence="daily",
        valid_units=["ms", "milliseconds", "s", "seconds"],
    ),
    "steps": MetricSpec(
        key="steps",
        unit="count",
        min_value=0,
        max_value=100000,
        description="Daily steps",
        direction=MetricDirection.HIGHER_IS_BETTER,
        aggregation=MetricAggregation.SUM,
        expected_cadence="daily",
        valid_units=["count", "steps"],
    ),

    # Subjective (user input)
    "sleep_quality": MetricSpec(
        key="sleep_quality",
        unit="score_1_5",
        min_value=1,
        max_value=5,
        description="Self-reported sleep quality",
        direction=MetricDirection.HIGHER_IS_BETTER,
        aggregation=MetricAggregation.MEAN,
        expected_cadence="daily",
        valid_units=["score_1_5"],
    ),
    "energy": MetricSpec(
        key="energy",
        unit="score_1_5",
        min_value=1,
        max_value=5,
        description="Self-reported energy",
        direction=MetricDirection.HIGHER_IS_BETTER,
        aggregation=MetricAggregation.MEAN,
        expected_cadence="daily",
        valid_units=["score_1_5"],
    ),
    "stress": MetricSpec(
        key="stress",
        unit="score_1_5",
        min_value=1,
        max_value=5,
        description="Self-reported stress",
        direction=MetricDirection.LOWER_IS_BETTER,
        aggregation=MetricAggregation.MEAN,
        expected_cadence="daily",
        valid_units=["score_1_5"],
    ),
}


def get_metric_spec(metric_key: str) -> MetricSpec:
    if metric_key not in METRICS:
        raise ValueError(f"Unknown metric_key: {metric_key}")
    return METRICS[metric_key]


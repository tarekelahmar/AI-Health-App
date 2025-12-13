from typing import Dict
from app.domain.metric_policy import (
    MetricPolicy,
    ChangePolicy,
    TrendPolicy,
    InstabilityPolicy,
)

METRIC_POLICIES: Dict[str, MetricPolicy] = {
    # Objective wearables
    "sleep_duration": MetricPolicy(
        metric_key="sleep_duration",
        allowed_insights={"change", "trend", "instability"},
        change=ChangePolicy(z_threshold=1.5),
        trend=TrendPolicy(slope_threshold=15),     # minutes/day
        instability=InstabilityPolicy(ratio_threshold=1.8),
    ),
    "sleep_efficiency": MetricPolicy(
        metric_key="sleep_efficiency",
        allowed_insights={"change", "trend"},
        change=ChangePolicy(z_threshold=1.2),
        trend=TrendPolicy(slope_threshold=1.0),    # % / day
    ),
    "resting_hr": MetricPolicy(
        metric_key="resting_hr",
        allowed_insights={"change", "trend"},
        change=ChangePolicy(z_threshold=1.3),
        trend=TrendPolicy(slope_threshold=0.8),    # bpm / day
    ),
    "hrv_rmssd": MetricPolicy(
        metric_key="hrv_rmssd",
        allowed_insights={"change", "trend", "instability"},
        change=ChangePolicy(z_threshold=1.5),
        trend=TrendPolicy(slope_threshold=1.0),
        instability=InstabilityPolicy(ratio_threshold=2.0),
    ),
    "steps": MetricPolicy(
        metric_key="steps",
        allowed_insights={"trend"},
        trend=TrendPolicy(slope_threshold=500),    # steps/day
    ),

    # Subjective
    "sleep_quality": MetricPolicy(
        metric_key="sleep_quality",
        allowed_insights={"trend", "instability"},
        trend=TrendPolicy(slope_threshold=0.3),
        instability=InstabilityPolicy(ratio_threshold=2.0),
    ),
    "energy": MetricPolicy(
        metric_key="energy",
        allowed_insights={"trend", "instability"},
        trend=TrendPolicy(slope_threshold=0.3),
        instability=InstabilityPolicy(ratio_threshold=2.0),
    ),
    "stress": MetricPolicy(
        metric_key="stress",
        allowed_insights={"trend", "instability"},
        trend=TrendPolicy(slope_threshold=0.3),
        instability=InstabilityPolicy(ratio_threshold=2.0),
    ),
}


def get_metric_policy(metric_key: str) -> MetricPolicy:
    if metric_key not in METRIC_POLICIES:
        raise ValueError(f"No policy defined for metric: {metric_key}")
    return METRIC_POLICIES[metric_key]


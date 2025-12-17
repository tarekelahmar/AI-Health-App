# AUDIT FIX: Use single metric registry
from app.domain.metric_registry import METRICS as CANONICAL_METRICS


def validate_value(metric_key: str, value: float) -> None:
    """
    AUDIT FIX: Updated to use MetricSpec from domain.metric_registry.
    """
    metric = CANONICAL_METRICS[metric_key]

    # MetricSpec uses min_value/max_value instead of valid_range
    if metric.min_value is not None and metric.max_value is not None:
        if not (metric.min_value <= value <= metric.max_value):
            raise ValueError(
                f"Value {value} out of range for {metric_key} ({metric.min_value}, {metric.max_value})"
            )


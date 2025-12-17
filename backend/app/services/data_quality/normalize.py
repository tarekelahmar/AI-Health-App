# AUDIT FIX: Use single metric registry
from app.domain.metric_registry import METRICS as CANONICAL_METRICS


def normalize_value(metric_key: str, value: float, unit: str) -> float:
    metric = CANONICAL_METRICS[metric_key]

    # For MVP: assume incoming units already correct
    # Unit conversion comes later
    if unit != metric.unit:
        raise ValueError(
            f"Unit mismatch for {metric_key}: got {unit}, expected {metric.unit}"
        )

    return float(value)


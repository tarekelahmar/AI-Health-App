# AUDIT FIX: Use single metric registry (Phase 1.1 unified registry)
from app.domain.metrics.registry import METRIC_REGISTRY as CANONICAL_METRICS


def normalize_value(metric_key: str, value: float, unit: str) -> float:
    metric = CANONICAL_METRICS[metric_key]

    # For MVP: assume incoming units already correct
    # Unit conversion comes later
    if unit != metric.unit:
        raise ValueError(
            f"Unit mismatch for {metric_key}: got {unit}, expected {metric.unit}"
        )

    return float(value)


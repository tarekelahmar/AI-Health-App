"""
Data quality helpers.

Phase 1.1:
- Normalization helpers for incoming values.

Phase 1.3:
- Per-value quality assessment via DataQualityService.
"""

# AUDIT FIX: Use single metric registry (Phase 1.1 unified registry)
from app.domain.metrics.registry import METRIC_REGISTRY as CANONICAL_METRICS
from app.services.data_quality.quality import DataQualityService, QualityAssessment  # re-export for convenience


def normalize_value(metric_key: str, value: float, unit: str) -> float:
    metric = CANONICAL_METRICS[metric_key]

    # For MVP: assume incoming units already correct
    # Unit conversion comes later
    if unit != metric.unit:
        raise ValueError(
            f"Unit mismatch for {metric_key}: got {unit}, expected {metric.unit}"
        )

    return float(value)



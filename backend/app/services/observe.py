from app.core.signal import Signal

from app.core.metrics import CANONICAL_METRICS
from app.services.data_quality.normalize import normalize_value
from app.services.data_quality.validate import validate_value
from app.services.data_quality.reliability import score_reliability

def observe_signal(
    *,
    user_id: int,
    metric_key: str,
    value: float,
    unit: str,
    timestamp,
    source: str,
) -> Signal:
    if metric_key not in CANONICAL_METRICS:
        raise ValueError(f"Unknown metric: {metric_key}")

    normalized = normalize_value(metric_key, value, unit)
    validate_value(metric_key, normalized)

    reliability = score_reliability(source)

    return Signal(
        user_id=user_id,
        metric_key=metric_key,
        value=normalized,
        unit=unit,
        timestamp=timestamp,
        source=source,
        reliability=reliability,
    )


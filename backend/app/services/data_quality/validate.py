from app.core.metrics import CANONICAL_METRICS


def validate_value(metric_key: str, value: float) -> None:
    metric = CANONICAL_METRICS[metric_key]

    if metric.valid_range:
        low, high = metric.valid_range

        if not (low <= value <= high):
            raise ValueError(
                f"Value {value} out of range for {metric_key} ({low}, {high})"
            )


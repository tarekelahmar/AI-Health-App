from app.domain.red_flags import RED_FLAGS


from typing import Optional, Dict, Any


def apply_guardrails(
    *,
    metric_key: str,
    values: list[float],
) -> Optional[Dict[str, Any]]:
    """
    Returns a guardrail insight if triggered.
    """
    if metric_key not in RED_FLAGS:
        return None

    rules = RED_FLAGS[metric_key]

    critical_low = rules.get("critical_low")
    critical_high = rules.get("critical_high")

    if critical_low is not None:
        if all(v <= critical_low for v in values):
            return {
                "title": "Health warning",
                "summary": rules["message"],
                "status": "detected",
                "confidence": 0.9,
            }

    if critical_high is not None:
        if all(v >= critical_high for v in values):
            return {
                "title": "Health warning",
                "summary": rules["message"],
                "status": "detected",
                "confidence": 0.9,
            }

    return None


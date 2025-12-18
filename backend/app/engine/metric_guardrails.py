from typing import Any, Dict, List, Optional

from app.domain.red_flags import RED_FLAGS


def apply_guardrails(
    *,
    metric_key: str,
    values: List[float],
) -> Optional[Dict[str, Any]]:
    """
    Legacy metric-level safety guardrails.

    This runs AFTER the primary safety gate and uses a simple RED_FLAGS
    table to trigger deterministic "health warning" insights when all of
    the recent values breach a critical low/high threshold.
    """
    if metric_key not in RED_FLAGS:
        return None

    rules = RED_FLAGS[metric_key]

    critical_low = rules.get("critical_low")
    critical_high = rules.get("critical_high")

    # If there is no recent data, do not emit a guardrail insight.
    if not values:
        return None

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



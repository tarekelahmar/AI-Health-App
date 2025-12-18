import json
from datetime import datetime
from typing import Dict, Any, List, Optional

from app.domain.safety.red_flags import evaluate_red_flags


def make_safety_insight_payload(
    *,
    user_id: int,
    triggers: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Create a safety insight payload from red flag triggers.

    Safety insights have confidence=1.0 (deterministic) and bypass
    normal suppression rules.
    """
    # One "umbrella" safety insight containing all triggers
    title = "Safety alert"
    summary = triggers[0]["message"] if triggers else "Safety alert triggered."

    # Extract metric_key from first trigger
    metric_key = triggers[0].get("metric_key") if triggers else None

    # Build evidence from triggers
    evidence = {}
    for trigger in triggers:
        if trigger.get("metric_key"):
            evidence[trigger["metric_key"]] = trigger.get("evidence", {}).get("value")

    # Build metadata that satisfies invariant requirements:
    # - must contain 'metric_key'
    # - must contain 'evidence' or 'status'
    metadata = {
        "type": "safety",
        "status": "safety",  # Satisfies invariant requirement
        "metric_key": metric_key,  # Satisfies invariant requirement
        "evidence": evidence,  # Satisfies invariant requirement
        "triggers": triggers,
        "severity": triggers[0].get("severity") if triggers else "medium",
        "action": triggers[0].get("action") if triggers else "monitor",
        "generated_at": datetime.utcnow().isoformat(),
    }

    return {
        "user_id": user_id,
        "title": title,
        "description": summary,
        "insight_type": "safety",         # domain uses insight_type; transformer maps to status
        "confidence_score": 1.0,          # safety is deterministic rule
        "metric_key": metric_key,
        "metadata_json": json.dumps(metadata),
    }


def run_safety_gate(
    *,
    user_id: int,
    latest_metrics: Dict[str, float],
    symptom_tags: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    triggers = evaluate_red_flags(latest_metrics=latest_metrics, symptom_tags=symptom_tags)
    if not triggers:
        return None
    return make_safety_insight_payload(user_id=user_id, triggers=triggers)


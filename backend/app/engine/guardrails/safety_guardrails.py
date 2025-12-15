import json
from datetime import datetime
from typing import Dict, Any, List, Optional

from app.domain.safety.red_flags import evaluate_red_flags


def make_safety_insight_payload(
    *,
    user_id: int,
    triggers: List[Dict[str, Any]],
) -> Dict[str, Any]:
    # One "umbrella" safety insight containing all triggers
    title = "Safety alert"
    summary = triggers[0]["message"] if triggers else "Safety alert triggered."
    metadata = {
        "type": "safety",
        "triggers": triggers,
        "generated_at": datetime.utcnow().isoformat(),
    }

    return {
        "user_id": user_id,
        "title": title,
        "description": summary,
        "insight_type": "safety",         # domain uses insight_type; transformer maps to status
        "confidence_score": 1.0,          # safety is deterministic rule
        "metric_key": triggers[0].get("metric_key") if triggers else None,
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


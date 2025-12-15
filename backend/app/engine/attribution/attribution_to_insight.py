from __future__ import annotations

import json

from typing import List, Optional

from datetime import datetime

from app.engine.attribution.attribution_types import AttributionResult

# IMPORTANT: This module builds a SAFE, STRUCTURED insight payload from attribution results.

# It does NOT claim causality. It describes observed associations with uncertainty.

def pick_best_attribution(attributions: List[AttributionResult]) -> Optional[AttributionResult]:
    if not attributions:
        return None
    # rank by |effect| * confidence (simple and robust for MVP)
    return sorted(attributions, key=lambda a: abs(a.effect_size) * a.confidence, reverse=True)[0]

def build_attribution_insight_domain_fields(
    *,
    user_id: int,
    attributions: List[AttributionResult],
    experiment_id: int,
    intervention_id: int,
    metric_key: str,
) -> dict:
    """
    Returns a dict of fields suitable for creating an Insight domain/ORM object,
    consistent with your existing Insight model fields:
      - user_id
      - insight_type
      - title
      - description
      - confidence_score
      - metadata_json
      - generated_at
    """
    best = pick_best_attribution(attributions)
    if not best:
        return {
            "user_id": user_id,
            "insight_type": "attribution",
            "title": f"No clear effect detected for {metric_key}",
            "description": "Not enough signal to attribute changes to the intervention yet. Keep collecting data.",
            "confidence_score": 0.2,
            "metadata_json": json.dumps({
                "type": "attribution",
                "metric_key": metric_key,
                "experiment_id": experiment_id,
                "intervention_id": intervention_id,
                "note": "No attribution results available or insufficient data.",
                "attributions": [],
            }),
            "generated_at": datetime.utcnow(),
        }

    direction_phrase = {
        "improved": "improved",
        "worsened": "worsened",
        "no_change": "did not materially change",
    }.get(best.direction, best.direction)

    # Keep language non-causal and non-diagnostic
    title = f"{metric_key} {direction_phrase} after intervention (lag {best.lag_days}d)"

    description = (
        "We observed a measurable change in this metric during the intervention period compared to baseline. "
        "This is an association (not proof of cause)."
    )

    # include top 3 lags for transparency
    ranked = sorted(attributions, key=lambda a: abs(a.effect_size) * a.confidence, reverse=True)
    top = ranked[:3]

    evidence = {
        "type": "attribution",
        "metric_key": metric_key,
        "experiment_id": experiment_id,
        "intervention_id": intervention_id,
        "best": {
            "lag_days": best.lag_days,
            "effect_size": best.effect_size,
            "direction": best.direction,
            "confidence": best.confidence,
            "coverage": best.coverage,
            "details": best.details,
        },
        "top_lags": [
            {
                "lag_days": a.lag_days,
                "effect_size": a.effect_size,
                "direction": a.direction,
                "confidence": a.confidence,
                "coverage": a.coverage,
                "details": a.details,
            }
            for a in top
        ],
        "safety": {
            "statement": "Association only. Not medical advice. If you have concerning symptoms, seek medical care."
        },
    }

    confidence = float(max(0.0, min(1.0, best.confidence)))

    return {
        "user_id": user_id,
        "insight_type": "attribution",
        "title": title,
        "description": description,
        "confidence_score": confidence,
        "metadata_json": json.dumps(evidence),
        "generated_at": datetime.utcnow(),
    }


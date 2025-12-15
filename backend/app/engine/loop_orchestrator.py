from __future__ import annotations

import json

from typing import Optional, Dict, Any

# Your existing E2 evaluation verdicts:
#   helpful / not_helpful / unclear / insufficient_data
# This update makes decisions *attribution-aware* when details are present.

def decide_next_step(
    *,
    evaluation: Any,
) -> Dict[str, Any]:
    """
    Input: EvaluationResult model/domain object.
    Output: A decision dict for LoopDecisionRepository.create(...)
    We remain conservative:
      - "harmful" (if you ever add it) or strong 'worsened' attribution => stop
      - helpful + good confidence => continue
      - unclear => adjust (change dosage/timing, or control confounders)
      - insufficient_data => extend (collect more days)
    """
    verdict = getattr(evaluation, "verdict", None) or getattr(evaluation, "result", None) or "unclear"
    confidence = float(getattr(evaluation, "confidence", 0.0) or 0.0)

    # details_json may be stored as JSON string; handle both
    details_raw = getattr(evaluation, "details_json", None)
    details: Dict[str, Any] = {}
    if isinstance(details_raw, str) and details_raw.strip():
        try:
            details = json.loads(details_raw)
        except Exception:
            details = {}
    elif isinstance(details_raw, dict):
        details = details_raw

    # Attribution details (if present)
    attr = details.get("attribution") or {}
    direction = attr.get("direction")  # improved/worsened/no_change
    effect_size = float(attr.get("effect_size", 0.0) or 0.0)
    best_lag = attr.get("best_lag_days")

    # Check for interaction notes (I3 - confounder-aware decision)
    interaction_note = details.get("interaction_note")
    if interaction_note and verdict == "helpful":
        action = "adjust"
        reason = interaction_note
    # Decision policy
    elif verdict in ("harmful",) or (direction == "worsened" and abs(effect_size) >= 0.5 and confidence >= 0.5):
        action = "stop"
        reason = "Evidence suggests this intervention may be worsening the target metric."
    elif verdict == "helpful" and confidence >= 0.6:
        action = "continue"
        reason = f"Helpful effect observed (best lag {best_lag}d). Continue and monitor."
    elif verdict == "not_helpful":
        action = "stop"
        reason = "No meaningful benefit detected. Stop and consider alternative intervention."
    elif verdict == "insufficient_data":
        action = "extend"
        reason = "Insufficient data coverage/adherence. Extend experiment duration and collect more data."
    else:
        action = "adjust"
        reason = "Effect is unclear. Adjust timing/dose or reduce confounders (e.g., caffeine/alcohol) and re-evaluate."

    metadata = {
        "verdict": verdict,
        "confidence": confidence,
        "attribution": {
            "direction": direction,
            "effect_size": effect_size,
            "best_lag_days": best_lag,
        } if attr else None,
        "notes": "Conservative decision logic. Not medical advice.",
    }

    return {
        "action": action,
        "reason": reason,
        "metadata_json": json.dumps(metadata),
    }

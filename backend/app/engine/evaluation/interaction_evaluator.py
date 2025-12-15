from typing import List, Dict, Any

from app.engine.attribution.interaction_effects import InteractionAttributionResult


def adjust_verdict_with_interactions(
    *,
    base_verdict: str,
    interactions: List[InteractionAttributionResult],
) -> Dict[str, Any]:
    """
    Adjusts verdict when interactions materially change outcomes.
    """
    if not interactions:
        return {
            "verdict": base_verdict,
            "note": "No major interactions detected.",
        }

    strong_negative = [
        i for i in interactions if i.delta_vs_control < -0.4
    ]

    if strong_negative:
        return {
            "verdict": "adjust",
            "note": (
                f"Intervention appears ineffective or harmful "
                f"when {strong_negative[0].confounder_key} is present."
            ),
        }

    return {
        "verdict": base_verdict,
        "note": "Effect consistent across confounder states.",
    }


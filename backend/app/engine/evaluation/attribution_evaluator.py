from typing import List, Optional

from statistics import mean

from app.engine.attribution.attribution_types import AttributionResult


class AttributionEvaluator:
    """
    Converts attribution results into an evaluation verdict.
    """

    def evaluate(
        self,
        attributions: List[AttributionResult],
    ) -> Optional[dict]:

        if not attributions:
            return {
                "verdict": "insufficient_data",
                "reason": "No attribution results available",
                "confidence": 0.0,
                "details": {},
            }

        # Pick strongest attribution by |effect_size| * confidence
        ranked = sorted(
            attributions,
            key=lambda a: abs(a.effect_size) * a.confidence,
            reverse=True,
        )

        best = ranked[0]

        score = abs(best.effect_size)
        confidence = best.confidence

        if confidence < 0.4:
            verdict = "unclear"
            reason = "Low confidence despite observed effect"
        elif score >= 0.5:
            verdict = "helpful" if best.direction == "improved" else "harmful"
            reason = f"Strong {best.direction} effect at lag {best.lag_days} days"
        elif score >= 0.2:
            verdict = "unclear"
            reason = f"Weak effect at lag {best.lag_days} days"
        else:
            verdict = "not_helpful"
            reason = "No meaningful effect detected"

        return {
            "verdict": verdict,
            "reason": reason,
            "confidence": round(confidence, 2),
            "details": {
                "best_lag_days": best.lag_days,
                "effect_size": best.effect_size,
                "direction": best.direction,
                "coverage": best.coverage,
                "metric_key": best.metric_key,
            },
        }


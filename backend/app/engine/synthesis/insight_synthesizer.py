from datetime import date, timedelta
from collections import defaultdict
from typing import List, Dict, Any


class InsightSynthesizer:
    def synthesize(
        self,
        user_id: int,
        insights: list,
        evaluations: list,
        adherence_events: list,
        period: str = "daily",
    ) -> Dict[str, Any]:
        # 1. Rank insights by importance
        ranked = sorted(
            insights,
            key=lambda i: (
                getattr(i, "insight_type", "") == "safety",
                getattr(i, "confidence_score", 0),
            ),
            reverse=True,
        )

        # 2. Group by metric
        by_metric = defaultdict(list)
        for i in ranked:
            metric_key = getattr(i, "metric_key", "unknown")
            by_metric[metric_key].append(i)

        # 3. Extract drivers
        drivers = []
        for e in evaluations:
            verdict = getattr(e, "verdict", None)
            if verdict == "helpful":
                drivers.append({
                    "intervention_id": getattr(e, "experiment_id", None),
                    "metric": getattr(e, "metric_key", "unknown"),
                    "effect": getattr(e, "percent_change", 0),
                })

        # 4. Build narrative
        headline = self._build_headline(by_metric, drivers)
        narrative = self._build_narrative(by_metric, drivers)

        return {
            "headline": headline,
            "narrative": narrative,
            "key_metrics": list(by_metric.keys())[:5],
            "drivers": drivers,
            "interventions": list({getattr(e, "experiment_id", None) for e in evaluations if getattr(e, "experiment_id", None)}),
            "outcomes": [getattr(e, "verdict", "unknown") for e in evaluations],
            "confidence": self._estimate_confidence(insights),
        }

    def _build_headline(self, by_metric, drivers):
        if drivers:
            return "Your recent changes appear to be working"
        if by_metric:
            metric_names = [m.replace("_", " ").title() for m in list(by_metric.keys())[:2]]
            return f"Changes detected in {', '.join(metric_names)}"
        return "No significant changes detected"

    def _build_narrative(self, by_metric, drivers):
        lines = []
        for metric, items in by_metric.items():
            if items:
                strongest = items[0]
                insight_type = getattr(strongest, "insight_type", "change")
                confidence = getattr(strongest, "confidence_score", 0)
                metric_name = metric.replace("_", " ").title()
                lines.append(
                    f"{metric_name} showed a {insight_type} "
                    f"with {int(confidence*100)}% confidence."
                )

        for d in drivers:
            lines.append(
                f"Intervention {d.get('intervention_id', 'unknown')} was associated with "
                f"a {round(d.get('effect', 0), 1)}% change."
            )

        return " ".join(lines) if lines else "No significant patterns detected."

    def _estimate_confidence(self, insights):
        if not insights:
            return 0
        confidences = [getattr(i, "confidence_score", 0) for i in insights]
        return int(sum(confidences) / len(confidences) * 100) if confidences else 0


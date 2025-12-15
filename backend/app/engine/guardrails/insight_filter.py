from typing import List
from app.engine.guardrails.policy import get_policy
from app.domain.safety.types import RiskLevel


def filter_insights(insights: List[dict]) -> List[dict]:
    """
    Drop insights that fail minimum trust thresholds.
    """
    passed = []

    for ins in insights:
        metric = ins.get("metric_key")
        if not metric:
            continue
        
        policy = get_policy(metric)

        confidence = ins.get("confidence", 0.0)
        coverage = ins.get("coverage", 0.0)
        effect = abs(ins.get("effect_size", 0.0))

        # Extract safety risk from evidence if present
        evidence = ins.get("evidence", {})
        safety = evidence.get("safety", {}) if isinstance(evidence, dict) else {}
        risk = safety.get("risk", "low") if isinstance(safety, dict) else "low"

        if confidence < policy.min_confidence:
            continue

        if coverage < policy.min_coverage:
            continue

        if effect < policy.min_effect_size:
            continue

        if risk == RiskLevel.HIGH.value:
            continue

        passed.append(ins)

    return passed


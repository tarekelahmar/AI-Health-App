from collections import defaultdict
from typing import List


def apply_escalation_rules(insights: List[dict]) -> List[dict]:
    """
    Require ≥2 independent signals before escalation.
    """
    grouped = defaultdict(list)
    for ins in insights:
        metric_key = ins.get("metric_key")
        if metric_key:
            grouped[metric_key].append(ins)

    final = []

    for metric, items in grouped.items():
        if len(items) >= 2:
            final.extend(items)
        else:
            # downgrade single-signal insights
            ins = items[0].copy()  # Avoid mutating original
            ins["status"] = "weak_signal"
            final.append(ins)

    return final


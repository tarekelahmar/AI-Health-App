from typing import List


def prune_driver_edges(edges: List[dict]) -> List[dict]:
    """
    Remove unsafe or weak edges from driver graph.
    """
    pruned = []
    for edge in edges:
        if edge.get("confidence", 0.0) < 0.6:
            continue
        if abs(edge.get("effect_size", 0.0)) < 0.2:
            continue
        safety = edge.get("safety", {})
        if isinstance(safety, dict) and safety.get("risk") == "high":
            continue
        pruned.append(edge)
    return pruned


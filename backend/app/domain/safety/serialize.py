from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict

from app.domain.safety.types import SafetyDecision


def safety_decision_to_dict(decision: SafetyDecision) -> Dict[str, Any]:
    """
    Convert SafetyDecision dataclass (and nested dataclasses/enums) to JSON-serializable dict.
    Enums become their `.value`.
    """
    raw = asdict(decision)

    # flatten enums to values
    def _normalize(obj):
        if isinstance(obj, dict):
            return {k: _normalize(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_normalize(x) for x in obj]
        # enums in dataclasses become their values in asdict() only if they were primitives;
        # but to be safe, handle objects with 'value'
        if hasattr(obj, "value"):
            return getattr(obj, "value")
        return obj

    return _normalize(raw)


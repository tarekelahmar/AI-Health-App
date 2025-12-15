from typing import Dict, List, Optional
from app.engine.safety.safety_service import SafetyService
from app.domain.safety.types import EvidenceGrade


def guard_protocol(protocol_payload: Dict, user_flags: Optional[Dict] = None) -> Dict:
    """
    Enforce safety + evidence before protocol surfacing.
    """
    guarded = []
    interventions = protocol_payload.get("interventions", [])
    
    for item in interventions:
        key = item.get("intervention_key") or item.get("key")
        if not key:
            guarded.append(item)  # Keep items without keys
            continue

        safety = SafetyService.evaluate_intervention(
            intervention_key=key,
            user_flags=user_flags,
            requested_boundary=item.get("boundary"),
            requested_evidence=item.get("evidence_grade"),
        )

        if not safety.allowed:
            continue

        if safety.evidence_grade in [EvidenceGrade.C, EvidenceGrade.D]:
            item["boundary"] = "experiment"

        item["safety"] = safety.to_dict()
        guarded.append(item)

    protocol_payload["interventions"] = guarded
    return protocol_payload


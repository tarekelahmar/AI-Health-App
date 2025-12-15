from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class ContraRule:
    intervention_key: str
    block_if: Dict[str, str]  # user flags -> expected value
    message: str
    severity: str  # "block" | "warn"


# MVP rules; expand with pregnancy, kidney disease, meds, etc.
CONTRA_RULES: List[ContraRule] = [
    ContraRule(
        intervention_key="melatonin",
        block_if={"pregnant": "true"},
        message="Avoid melatonin during pregnancy unless advised by a clinician.",
        severity="warn",
    ),
    ContraRule(
        intervention_key="magnesium",
        block_if={"kidney_disease": "true"},
        message="Magnesium supplements can be risky in kidney disease. Consult a clinician.",
        severity="warn",
    ),
]


def check_contraindications(
    *,
    intervention_key: str,
    user_flags: Dict[str, str],
) -> List[Dict[str, str]]:
    hits = []
    for rule in CONTRA_RULES:
        if rule.intervention_key != intervention_key:
            continue
        ok = True
        for k, expected in rule.block_if.items():
            if str(user_flags.get(k, "")).lower() != expected.lower():
                ok = False
                break
        if ok:
            hits.append({"severity": rule.severity, "message": rule.message})
    return hits


from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from .types import EvidenceGrade, RiskLevel


@dataclass(frozen=True)
class InterventionSpec:
    """
    Minimal safety + evidence metadata for an intervention.
    This is NOT medical advice. It's guardrails metadata.
    """
    key: str
    display_name: str
    default_risk: RiskLevel
    evidence_grade: EvidenceGrade
    contraindications: List[str]          # flags like "kidney_disease", "pregnant"
    interactions: List[str]              # flags like "warfarin", "levothyroxine"
    notes: Optional[str] = None


# MVP registry: expand over time.
INTERVENTIONS: Dict[str, InterventionSpec] = {
    "magnesium_glycinate": InterventionSpec(
        key="magnesium_glycinate",
        display_name="Magnesium (glycinate)",
        default_risk=RiskLevel.LOW,
        evidence_grade=EvidenceGrade.B,
        contraindications=["kidney_disease"],
        interactions=["tetracycline_antibiotics", "levothyroxine"],
        notes="Often used for sleep/support; separate from some meds by 4+ hours.",
    ),
    "melatonin": InterventionSpec(
        key="melatonin",
        display_name="Melatonin",
        default_risk=RiskLevel.MODERATE,
        evidence_grade=EvidenceGrade.B,
        contraindications=["pregnant", "trying_to_conceive"],
        interactions=["anticoagulants", "immunosuppressants"],
        notes="Use lowest effective dose; avoid long-term daily use without clinician input.",
    ),
    "omega_3": InterventionSpec(
        key="omega_3",
        display_name="Omega-3 (EPA/DHA)",
        default_risk=RiskLevel.LOW,
        evidence_grade=EvidenceGrade.B,
        contraindications=["bleeding_disorder"],
        interactions=["warfarin", "anticoagulants"],
        notes="Bleeding risk at high doses; disclose to clinician if on blood thinners.",
    ),
}


def get_intervention_spec(key: str) -> Optional[InterventionSpec]:
    return INTERVENTIONS.get(key)


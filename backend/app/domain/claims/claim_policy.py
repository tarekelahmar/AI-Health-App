"""
X3: Evidence Grading & Claim Boundaries

Formalizes allowed language for insights and narratives based on evidence strength.
Enforces that narratives and insights use only these verbs, LLM translations adhere to them,
and the UI displays evidence grade and uncertainty.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Literal, Optional


class ClaimStrength(str, Enum):
    """Strength of a claim based on evidence quality."""
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"


class EvidenceGrade(str, Enum):
    """Evidence grade (A=strongest, D=weakest)."""
    A = "A"  # High-quality, reproducible, large sample
    B = "B"  # Good quality, moderate sample
    C = "C"  # Moderate quality, small sample
    D = "D"  # Low quality, very small sample or high uncertainty


@dataclass(frozen=True)
class ClaimPolicy:
    """Policy defining allowed verbs and language for a given evidence grade."""
    grade: EvidenceGrade
    strength: ClaimStrength
    allowed_verbs: List[str]
    allowed_modifiers: List[str]
    disallowed_verbs: List[str]
    uncertainty_required: bool  # Must mention uncertainty
    example_phrases: List[str]


# Define claim policies for each evidence grade
CLAIM_POLICIES: dict[EvidenceGrade, ClaimPolicy] = {
    EvidenceGrade.A: ClaimPolicy(
        grade=EvidenceGrade.A,
        strength=ClaimStrength.STRONG,
        allowed_verbs=[
            "improves", "increases", "decreases", "reduces", "enhances",
            "correlates with", "is associated with", "shows",
        ],
        allowed_modifiers=[
            "significantly", "consistently", "reliably",
        ],
        disallowed_verbs=[
            "causes", "guarantees", "ensures", "proves",
        ],
        uncertainty_required=False,
        example_phrases=[
            "significantly improves",
            "is consistently associated with",
            "shows a reliable increase",
        ],
    ),
    EvidenceGrade.B: ClaimPolicy(
        grade=EvidenceGrade.B,
        strength=ClaimStrength.MODERATE,
        allowed_verbs=[
            "appears to improve", "may increase", "suggests",
            "is associated with", "tends to", "shows",
        ],
        allowed_modifiers=[
            "likely", "probably", "often",
        ],
        disallowed_verbs=[
            "causes", "guarantees", "ensures", "proves", "definitely",
        ],
        uncertainty_required=True,
        example_phrases=[
            "appears to improve",
            "may be associated with",
            "suggests a likely increase",
        ],
    ),
    EvidenceGrade.C: ClaimPolicy(
        grade=EvidenceGrade.C,
        strength=ClaimStrength.WEAK,
        allowed_verbs=[
            "might improve", "could increase", "possibly",
            "may be associated with", "suggests a potential",
        ],
        allowed_modifiers=[
            "possibly", "potentially", "uncertain",
        ],
        disallowed_verbs=[
            "improves", "increases", "causes", "guarantees", "ensures", "proves",
            "definitely", "significantly", "consistently",
        ],
        uncertainty_required=True,
        example_phrases=[
            "might be associated with",
            "could potentially improve",
            "suggests a possible increase (uncertain)",
        ],
    ),
    EvidenceGrade.D: ClaimPolicy(
        grade=EvidenceGrade.D,
        strength=ClaimStrength.WEAK,
        allowed_verbs=[
            "might suggest", "could indicate", "possibly hints at",
            "uncertain association with",
        ],
        allowed_modifiers=[
            "uncertain", "unclear", "inconclusive", "limited evidence",
        ],
        disallowed_verbs=[
            "improves", "increases", "causes", "guarantees", "ensures", "proves",
            "definitely", "significantly", "consistently", "appears to",
        ],
        uncertainty_required=True,
        example_phrases=[
            "uncertain association (limited evidence)",
            "might suggest (inconclusive)",
            "could indicate (unclear)",
        ],
    ),
}


def get_evidence_grade(
    *,
    confidence: float,
    sample_size: int,
    coverage: float,
    effect_size: Optional[float] = None,
    p_value: Optional[float] = None,
) -> EvidenceGrade:
    """
    Determine evidence grade from statistical metrics.
    
    Grade A: confidence >= 0.8, sample_size >= 30, coverage >= 0.7, effect_size >= 0.5
    Grade B: confidence >= 0.6, sample_size >= 14, coverage >= 0.5
    Grade C: confidence >= 0.4, sample_size >= 7, coverage >= 0.3
    Grade D: everything else
    """
    if confidence >= 0.8 and sample_size >= 30 and coverage >= 0.7:
        if effect_size and effect_size >= 0.5:
            return EvidenceGrade.A
        if p_value and p_value < 0.01:
            return EvidenceGrade.A
    
    if confidence >= 0.6 and sample_size >= 14 and coverage >= 0.5:
        return EvidenceGrade.B
    
    if confidence >= 0.4 and sample_size >= 7 and coverage >= 0.3:
        return EvidenceGrade.C
    
    return EvidenceGrade.D


def get_claim_policy(grade: EvidenceGrade) -> ClaimPolicy:
    """Get the claim policy for a given evidence grade."""
    return CLAIM_POLICIES[grade]


def validate_claim_language(text: str, grade: EvidenceGrade) -> tuple[bool, List[str]]:
    """
    Validate that text adheres to claim policy for the given grade.
    
    Returns (is_valid, violations).
    """
    policy = get_claim_policy(grade)
    violations: List[str] = []
    text_lower = text.lower()
    
    # Check for disallowed verbs
    for verb in policy.disallowed_verbs:
        if verb.lower() in text_lower:
            violations.append(f"Disallowed verb '{verb}' found (grade {grade.value})")
    
    # Check for uncertainty requirement
    if policy.uncertainty_required:
        uncertainty_keywords = ["uncertain", "unclear", "may", "might", "could", "possibly", "potentially", "suggests"]
        has_uncertainty = any(kw in text_lower for kw in uncertainty_keywords)
        if not has_uncertainty:
            violations.append(f"Uncertainty must be mentioned for grade {grade.value}")
    
    # Check for allowed verbs (at least one should be present)
    has_allowed_verb = any(verb.lower() in text_lower for verb in policy.allowed_verbs)
    if not has_allowed_verb and len(policy.allowed_verbs) > 0:
        violations.append(f"No allowed verbs found for grade {grade.value}")
    
    return len(violations) == 0, violations


def suggest_claim_language(grade: EvidenceGrade, metric_key: str, direction: str) -> str:
    """
    Suggest claim language that adheres to the policy for the given grade.
    
    This can be used by LLM prompts or deterministic narrative generation.
    """
    policy = get_claim_policy(grade)
    
    # Select an appropriate example phrase based on direction
    if direction == "positive":
        verb = "improves" if grade == EvidenceGrade.A else "appears to improve" if grade == EvidenceGrade.B else "might improve"
    elif direction == "negative":
        verb = "decreases" if grade == EvidenceGrade.A else "appears to decrease" if grade == EvidenceGrade.B else "might decrease"
    else:
        verb = "is associated with" if grade in [EvidenceGrade.A, EvidenceGrade.B] else "might be associated with"
    
    # Build phrase
    if policy.uncertainty_required and grade in [EvidenceGrade.C, EvidenceGrade.D]:
        phrase = f"{verb} {metric_key} (uncertain)"
    else:
        phrase = f"{verb} {metric_key}"
    
    return phrase


from __future__ import annotations

from typing import Any, Dict, Optional

from app.domain.safety.registry import get_intervention_spec
from app.domain.safety.types import BoundaryCategory, EvidenceGrade, RiskLevel, SafetyDecision, SafetyIssue
from app.domain.safety.user_flags import UserSafetyFlags


def _max_risk(a: RiskLevel, b: RiskLevel) -> RiskLevel:
    order = {RiskLevel.LOW: 0, RiskLevel.MODERATE: 1, RiskLevel.HIGH: 2}
    return a if order[a] >= order[b] else b


class SafetyService:
    """
    Hard guardrails around interventions/protocol surfacing.
    - Does NOT diagnose.
    - Does NOT prescribe.
    - Only blocks/labels based on known contraindication flags.
    """

    @staticmethod
    def evaluate_intervention(
        *,
        intervention_key: str,
        user_flags: Optional[Dict[str, Any]] = None,
        requested_boundary: Optional[str] = None,
        requested_evidence: Optional[str] = None,
    ) -> SafetyDecision:
        spec = get_intervention_spec(intervention_key)

        # Default: unknown interventions are allowed but downgraded and bounded.
        if spec is None:
            return SafetyDecision(
                allowed=True,
                risk=RiskLevel.MODERATE,
                issues=[
                    SafetyIssue(
                        code="unknown_intervention",
                        severity=RiskLevel.MODERATE,
                        message="This intervention is not in the safety registry yet. Treat as experimental and proceed cautiously.",
                        details={"intervention_key": intervention_key},
                    )
                ],
                boundary=BoundaryCategory.EXPERIMENT,
                evidence_grade=EvidenceGrade.D,
            )

        flags = UserSafetyFlags.from_dict(user_flags)
        user_flag_set = set(flags.to_flag_list())

        issues = []
        risk = spec.default_risk

        # Contraindications
        for c in spec.contraindications:
            if c in user_flag_set:
                issues.append(
                    SafetyIssue(
                        code="contraindication",
                        severity=RiskLevel.HIGH,
                        message=f"User has contraindication flag '{c}' for {spec.display_name}.",
                        details={"flag": c, "intervention_key": intervention_key},
                    )
                )
                risk = _max_risk(risk, RiskLevel.HIGH)

        # Interactions
        for i in spec.interactions:
            if i in user_flag_set:
                issues.append(
                    SafetyIssue(
                        code="interaction",
                        severity=RiskLevel.MODERATE,
                        message=f"User has interaction flag '{i}' for {spec.display_name}.",
                        details={"flag": i, "intervention_key": intervention_key},
                    )
                )
                risk = _max_risk(risk, RiskLevel.MODERATE)

        # Boundary
        boundary = BoundaryCategory.EXPERIMENT
        if requested_boundary:
            try:
                boundary = BoundaryCategory(requested_boundary)
            except Exception:
                issues.append(
                    SafetyIssue(
                        code="invalid_boundary",
                        severity=RiskLevel.LOW,
                        message="Invalid boundary requested; defaulting to 'experiment'.",
                        details={"requested_boundary": requested_boundary},
                    )
                )
                boundary = BoundaryCategory.EXPERIMENT
        else:
            # Default boundary is based on risk: higher risk => experiment only.
            boundary = BoundaryCategory.EXPERIMENT if risk != RiskLevel.LOW else BoundaryCategory.LIFESTYLE

        # Evidence grade
        evidence = spec.evidence_grade
        if requested_evidence:
            try:
                evidence = EvidenceGrade(requested_evidence)
            except Exception:
                issues.append(
                    SafetyIssue(
                        code="invalid_evidence_grade",
                        severity=RiskLevel.LOW,
                        message="Invalid evidence grade requested; using registry grade.",
                        details={"requested_evidence": requested_evidence},
                    )
                )

        # Hard block if any HIGH contraindications.
        allowed = not any(i.severity == RiskLevel.HIGH and i.code == "contraindication" for i in issues)

        return SafetyDecision(
            allowed=allowed,
            risk=risk,
            issues=issues,
            boundary=boundary,
            evidence_grade=evidence,
        )

    @staticmethod
    def attach_safety_metadata(
        *,
        intervention_key: str,
        user_flags: Optional[Dict[str, Any]] = None,
        requested_boundary: Optional[str] = None,
        requested_evidence: Optional[str] = None,
    ) -> Dict[str, Any]:
        decision = SafetyService.evaluate_intervention(
            intervention_key=intervention_key,
            user_flags=user_flags,
            requested_boundary=requested_boundary,
            requested_evidence=requested_evidence,
        )
        return decision.to_dict()


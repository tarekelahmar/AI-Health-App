import json
from typing import Optional
from sqlalchemy.orm import Session
from app.domain.models.intervention import Intervention
from app.engine.safety.safety_service import SafetyService
from app.domain.safety.user_flags import UserSafetyFlags
from app.core.invariants import validate_intervention_invariants, InvariantViolation

class InterventionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_with_safety(
        self,
        user_id: int,
        key: str,
        name: str,
        category: Optional[str] = None,
        dosage: Optional[str] = None,
        schedule: Optional[str] = None,
        notes: Optional[str] = None,
        user_flags: Optional[dict] = None,
    ) -> Intervention:
        """
        (K3) Safety is evaluated at creation time.
        - If HIGH contraindication => hard block (raise ValueError).
        - Otherwise persist safety metadata on the Intervention row.
        """
        safety = SafetyService()
        flags = UserSafetyFlags.from_dict(user_flags)
        decision = safety.evaluate_intervention(intervention_key=key, user_flags=user_flags)

        if not decision.allowed:
            # Hard block unsafe interventions at the API boundary.
            reasons = ", ".join([i.code for i in decision.issues]) if decision.issues else "unsafe"
            raise ValueError(f"Intervention blocked by safety rules: {reasons}")

        # Convert SafetyIssue objects to dicts for JSON serialization
        issues_dicts = []
        for issue in decision.issues:
            issues_dicts.append({
                "code": issue.code,
                "severity": issue.severity.value if hasattr(issue.severity, 'value') else str(issue.severity),
                "message": issue.message,
                "details": issue.details,
            })

        safety_risk_level = decision.risk.value if hasattr(decision.risk, 'value') else str(decision.risk)
        safety_evidence_grade = decision.evidence_grade.value if hasattr(decision.evidence_grade, 'value') else str(decision.evidence_grade)
        safety_boundary = decision.boundary.value if hasattr(decision.boundary, 'value') else str(decision.boundary)

        # X1: Validate invariants before creation
        try:
            validate_intervention_invariants(
                user_id=user_id,
                key=key,
                name=name,
                safety_risk_level=safety_risk_level,
                safety_evidence_grade=safety_evidence_grade,
                safety_boundary=safety_boundary,
            )
        except InvariantViolation as e:
            # Hard-fail: skip object creation and surface safe fallback message
            raise ValueError(f"Intervention creation blocked: {e.message}")

        row = Intervention(
            user_id=user_id,
            key=key,
            name=name,
            category=category,
            dosage=dosage,
            schedule=schedule,
            notes=notes,
            safety_risk_level=safety_risk_level,
            safety_evidence_grade=safety_evidence_grade,
            safety_boundary=safety_boundary,
            safety_issues_json=json.dumps(issues_dicts, default=str),
            safety_notes="Informational only. Not medical advice.",
        )

        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_by_user(self, user_id: int) -> list[Intervention]:
        return self.db.query(Intervention).filter(Intervention.user_id == user_id).order_by(Intervention.created_at.desc()).all()

    def get(self, intervention_id: int) -> Optional[Intervention]:
        return self.db.query(Intervention).filter(Intervention.id == intervention_id).first()

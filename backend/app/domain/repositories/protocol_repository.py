import json
from typing import Optional
from sqlalchemy.orm import Session
from app.domain.models.protocol import Protocol
from app.domain.models.intervention import Intervention

class ProtocolRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_with_safety_summary(
        self,
        user_id: int,
        title: str,
        description: Optional[str],
        interventions: Optional[list[dict]],
    ) -> Protocol:
        """
        (K3) Protocol stores:
        - interventions_json: raw list for MVP
        - safety_summary_json: aggregated summary for UI + policy
        """
        interventions = interventions or []

        # Aggregate based on intervention rows (if intervention_id present) or embedded safety fields.
        blocked: list[dict] = []
        warnings: list[dict] = []
        highest_risk = "low"
        boundary = "informational"

        def _risk_rank(r: str) -> int:
            return {"low": 0, "moderate": 1, "high": 2}.get(r or "low", 0)

        def _boundary_rank(b: str) -> int:
            return {"informational": 0, "lifestyle": 1, "experiment": 2}.get(b or "informational", 0)

        for item in interventions:
            # Option A: reference an intervention row
            intervention_id = item.get("intervention_id")
            if intervention_id:
                row = self.db.query(Intervention).filter(Intervention.id == intervention_id, Intervention.user_id == user_id).first()
                if row:
                    r = row.safety_risk_level or "low"
                    b = row.safety_boundary or "informational"
                    if _risk_rank(r) > _risk_rank(highest_risk):
                        highest_risk = r
                    if _boundary_rank(b) > _boundary_rank(boundary):
                        boundary = b
                    # Issues list
                    try:
                        issues = json.loads(row.safety_issues_json or "[]")
                    except Exception:
                        issues = []
                    if r == "high":
                        blocked.append({"intervention_id": row.id, "key": row.key, "issues": issues})
                    elif issues:
                        warnings.append({"intervention_id": row.id, "key": row.key, "issues": issues})
                continue

            # Option B: embedded safety metadata (fallback)
            r = item.get("safety_risk_level") or "low"
            b = item.get("safety_boundary") or "informational"
            if _risk_rank(r) > _risk_rank(highest_risk):
                highest_risk = r
            if _boundary_rank(b) > _boundary_rank(boundary):
                boundary = b
            issues = item.get("safety_issues") or []
            if r == "high":
                blocked.append({"key": item.get("key"), "issues": issues})
            elif issues:
                warnings.append({"key": item.get("key"), "issues": issues})

        summary = {
            "highest_risk": highest_risk,
            "boundary": boundary,
            "blocked": blocked,
            "warnings": warnings,
            "notes": "Informational only. Not medical advice.",
        }

        row = Protocol(
            user_id=user_id,
            title=title,
            description=description,
            interventions_json=json.dumps(interventions),
            safety_summary_json=json.dumps(summary),
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_by_user(self, user_id: int) -> list[Protocol]:
        return self.db.query(Protocol).filter(Protocol.user_id == user_id).order_by(Protocol.created_at.desc()).all()

    def get(self, protocol_id: int) -> Optional[Protocol]:
        return self.db.query(Protocol).filter(Protocol.id == protocol_id).first()

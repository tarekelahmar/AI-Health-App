from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from app.domain.models.symptom import Symptom


class SymptomRepository:
    """Data access for Symptom logs."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        user_id: int,
        symptom_name: str,
        severity: str,
        frequency: str,
        notes: str = "",
        timestamp: Optional[datetime] = None,
    ) -> Symptom:
        symptom = Symptom(
            user_id=user_id,
            symptom_name=symptom_name,
            severity=severity,
            frequency=frequency,
            notes=notes,
            timestamp=timestamp or datetime.utcnow(),
        )
        self.db.add(symptom)
        self.db.commit()
        self.db.refresh(symptom)
        return symptom

    def list_recent(
        self,
        user_id: int,
        days: int = 30,
    ) -> List[Symptom]:
        """List symptoms for the last N days."""
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(days=days)
        return (
            self.db.query(Symptom)
            .filter(
                Symptom.user_id == user_id,
                Symptom.timestamp >= cutoff,
            )
            .order_by(Symptom.timestamp.desc())
            .all()
        )

    def list_by_name(
        self,
        user_id: int,
        symptom_name: str,
    ) -> List[Symptom]:
        return (
            self.db.query(Symptom)
            .filter(
                Symptom.user_id == user_id,
                Symptom.symptom_name == symptom_name,
            )
            .order_by(Symptom.timestamp.desc())
            .all()
        )


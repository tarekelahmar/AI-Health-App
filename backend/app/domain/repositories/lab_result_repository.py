from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from app.domain.models.lab_result import LabResult


class LabResultRepository:
    """Data access for LabResult entities."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, lab_id: int) -> Optional[LabResult]:
        return (
            self.db.query(LabResult)
            .filter(LabResult.id == lab_id)
            .first()
        )

    def create(
        self,
        *,
        user_id: int,
        test_name: str,
        value: float,
        unit: str,
        reference_range: str = "",
        timestamp: Optional[datetime] = None,
        lab_name: Optional[str] = None,
    ) -> LabResult:
        lab = LabResult(
            user_id=user_id,
            test_name=test_name,
            value=value,
            unit=unit,
            reference_range=reference_range,
            timestamp=timestamp or datetime.utcnow(),
            lab_name=lab_name or "",
        )
        self.db.add(lab)
        self.db.commit()
        self.db.refresh(lab)
        return lab

    def list_for_user(
        self,
        user_id: int,
        limit: int = 100,
        offset: int = 0,
    ) -> List[LabResult]:
        return (
            self.db.query(LabResult)
            .filter(LabResult.user_id == user_id)
            .order_by(LabResult.timestamp.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def list_for_user_in_range(
        self,
        user_id: int,
        start: datetime,
        end: datetime,
        test_name: Optional[str] = None,
    ) -> List[LabResult]:
        q = (
            self.db.query(LabResult)
            .filter(
                LabResult.user_id == user_id,
                LabResult.timestamp >= start,
                LabResult.timestamp <= end,
            )
        )
        if test_name:
            q = q.filter(LabResult.test_name == test_name)
        return q.order_by(LabResult.timestamp.asc()).all()

    def get_latest_for_test(
        self,
        user_id: int,
        test_name: str,
    ) -> Optional[LabResult]:
        return (
            self.db.query(LabResult)
            .filter(
                LabResult.user_id == user_id,
                LabResult.test_name == test_name,
            )
            .order_by(LabResult.timestamp.desc())
            .first()
        )


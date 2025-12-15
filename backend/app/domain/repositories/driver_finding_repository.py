from __future__ import annotations

from typing import List
from sqlalchemy.orm import Session

from app.domain.models.driver_finding import DriverFinding


class DriverFindingRepository:
    def __init__(self, db: Session):
        self.db = db

    def upsert_finding(self, finding: DriverFinding) -> DriverFinding:
        """
        Upsert a driver finding.
        Uses (user_id, exposure_key, metric_key, lag_days, window_start, window_end) as unique key.
        """
        existing = (
            self.db.query(DriverFinding)
            .filter(
                DriverFinding.user_id == finding.user_id,
                DriverFinding.exposure_key == finding.exposure_key,
                DriverFinding.metric_key == finding.metric_key,
                DriverFinding.lag_days == finding.lag_days,
                DriverFinding.window_start == finding.window_start,
                DriverFinding.window_end == finding.window_end,
            )
            .first()
        )

        if existing:
            # Update existing
            existing.direction = finding.direction
            existing.effect_size = finding.effect_size
            existing.confidence = finding.confidence
            existing.coverage = finding.coverage
            existing.n_exposure_days = finding.n_exposure_days
            existing.n_total_days = finding.n_total_days
            existing.details_json = finding.details_json
            self.db.add(existing)
            self.db.commit()
            self.db.refresh(existing)
            return existing

        self.db.add(finding)
        self.db.commit()
        self.db.refresh(finding)
        return finding

    def list_recent(self, user_id: int, limit: int = 50) -> List[DriverFinding]:
        """List recent driver findings for a user"""
        return (
            self.db.query(DriverFinding)
            .filter(DriverFinding.user_id == user_id)
            .order_by(DriverFinding.created_at.desc())
            .limit(limit)
            .all()
        )

    def list_by_metric(self, user_id: int, metric_key: str, limit: int = 50) -> List[DriverFinding]:
        """List driver findings for a specific metric"""
        return (
            self.db.query(DriverFinding)
            .filter(
                DriverFinding.user_id == user_id,
                DriverFinding.metric_key == metric_key,
            )
            .order_by(DriverFinding.confidence.desc(), DriverFinding.effect_size.desc())
            .limit(limit)
            .all()
        )


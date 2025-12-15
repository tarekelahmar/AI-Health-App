from __future__ import annotations

from typing import List, Optional
from sqlalchemy.orm import Session

from app.domain.models.personal_driver import PersonalDriver


class PersonalDriverRepository:
    def __init__(self, db: Session):
        self.db = db

    def upsert_driver(self, driver: PersonalDriver) -> PersonalDriver:
        """
        Upsert a personal driver.
        Uses (user_id, driver_key, outcome_metric, lag_days) as unique key.
        """
        existing = (
            self.db.query(PersonalDriver)
            .filter(
                PersonalDriver.user_id == driver.user_id,
                PersonalDriver.driver_key == driver.driver_key,
                PersonalDriver.outcome_metric == driver.outcome_metric,
                PersonalDriver.lag_days == driver.lag_days,
            )
            .first()
        )

        if existing:
            # Update existing
            existing.effect_size = driver.effect_size
            existing.direction = driver.direction
            existing.variance_explained = driver.variance_explained
            existing.confidence = driver.confidence
            existing.stability = driver.stability
            existing.sample_size = driver.sample_size
            self.db.add(existing)
            self.db.commit()
            self.db.refresh(existing)
            return existing

        self.db.add(driver)
        self.db.commit()
        self.db.refresh(driver)
        return driver

    def list_for_user(self, user_id: int, limit: int = 100) -> List[PersonalDriver]:
        """List personal drivers for a user, ranked by confidence * abs(effect_size)"""
        return (
            self.db.query(PersonalDriver)
            .filter(PersonalDriver.user_id == user_id)
            .order_by(
                (PersonalDriver.confidence * PersonalDriver.effect_size).desc()
            )
            .limit(limit)
            .all()
        )

    def list_by_outcome(self, user_id: int, outcome_metric: str, limit: int = 50) -> List[PersonalDriver]:
        """List personal drivers for a specific outcome metric"""
        return (
            self.db.query(PersonalDriver)
            .filter(
                PersonalDriver.user_id == user_id,
                PersonalDriver.outcome_metric == outcome_metric,
            )
            .order_by(
                (PersonalDriver.confidence * PersonalDriver.effect_size).desc()
            )
            .limit(limit)
            .all()
        )

    def get_top_positive(self, user_id: int, outcome_metric: str, limit: int = 10) -> List[PersonalDriver]:
        """Get top positive drivers for an outcome"""
        return (
            self.db.query(PersonalDriver)
            .filter(
                PersonalDriver.user_id == user_id,
                PersonalDriver.outcome_metric == outcome_metric,
                PersonalDriver.direction == "positive",
            )
            .order_by(
                (PersonalDriver.confidence * PersonalDriver.effect_size).desc()
            )
            .limit(limit)
            .all()
        )

    def get_top_negative(self, user_id: int, outcome_metric: str, limit: int = 10) -> List[PersonalDriver]:
        """Get top negative drivers for an outcome"""
        return (
            self.db.query(PersonalDriver)
            .filter(
                PersonalDriver.user_id == user_id,
                PersonalDriver.outcome_metric == outcome_metric,
                PersonalDriver.direction == "negative",
            )
            .order_by(
                (PersonalDriver.confidence * abs(PersonalDriver.effect_size)).desc()
            )
            .limit(limit)
            .all()
        )

    def delete_for_user(self, user_id: int) -> int:
        """Delete all personal drivers for a user (for recomputation)"""
        deleted = (
            self.db.query(PersonalDriver)
            .filter(PersonalDriver.user_id == user_id)
            .delete()
        )
        self.db.commit()
        return deleted


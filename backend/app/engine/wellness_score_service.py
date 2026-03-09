"""
Wellness score service — orchestrates computation, persistence, and retrieval.

Gathers data from HealthDataPoint and DailyCheckIn, fetches baselines,
calls the scoring engine, and stores/retrieves WellnessScore records.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.domain.models.baseline import Baseline
from app.domain.models.daily_checkin import DailyCheckIn
from app.domain.models.health_data_point import HealthDataPoint
from app.domain.models.wellness_score import WellnessScore
from app.engine.wellness_score import (
    OBJECTIVE_SIGNALS,
    SUBJECTIVE_SIGNALS,
    ScoreContributingFactor,
    WellnessScoreResult,
    compute_wellness_score,
)

logger = logging.getLogger(__name__)


def _get_baselines(db: Session, user_id: int) -> Dict[str, Tuple[float, float]]:
    """Fetch all baselines for a user as {metric_key: (center, spread)}."""
    rows = db.query(Baseline).filter(Baseline.user_id == user_id).all()
    return {row.metric_type: (row.mean, row.std) for row in rows if row.std > 0}


def _get_recent_objective_values(
    db: Session, user_id: int, target_date: date
) -> Dict[str, float]:
    """Get the most recent objective metric values for the target date."""
    start = datetime.combine(target_date, datetime.min.time())
    end = datetime.combine(target_date, datetime.max.time())

    values: Dict[str, float] = {}

    for metric_key in OBJECTIVE_SIGNALS:
        row = (
            db.query(HealthDataPoint)
            .filter(
                HealthDataPoint.user_id == user_id,
                HealthDataPoint.metric_type == metric_key,
                HealthDataPoint.timestamp >= start,
                HealthDataPoint.timestamp <= end,
            )
            .order_by(HealthDataPoint.timestamp.desc())
            .first()
        )
        if row and row.value is not None:
            values[metric_key] = row.value

    return values


def _get_subjective_values(
    db: Session, user_id: int, target_date: date
) -> Dict[str, float]:
    """Get subjective metric values from HealthDataPoint (bridged from DailyCheckIn)."""
    start = datetime.combine(target_date, datetime.min.time())
    end = datetime.combine(target_date, datetime.max.time())

    values: Dict[str, float] = {}

    for metric_key in SUBJECTIVE_SIGNALS:
        row = (
            db.query(HealthDataPoint)
            .filter(
                HealthDataPoint.user_id == user_id,
                HealthDataPoint.metric_type == metric_key,
                HealthDataPoint.timestamp >= start,
                HealthDataPoint.timestamp <= end,
            )
            .order_by(HealthDataPoint.timestamp.desc())
            .first()
        )
        if row and row.value is not None:
            values[metric_key] = row.value

    return values


def _factors_to_json(factors: List[ScoreContributingFactor]) -> List[dict]:
    """Convert ScoreContributingFactor list to JSON-serializable dicts."""
    return [
        {
            "metric_key": f.metric_key,
            "label": f.label,
            "z_score": f.z_score,
            "weight": f.weight,
            "direction": f.direction,
            "category": f.category,
        }
        for f in factors
    ]


def compute_and_store(
    db: Session,
    user_id: int,
    target_date: Optional[date] = None,
) -> WellnessScore:
    """
    Compute wellness score for a user on a given date and persist it.

    If target_date is None, uses today.
    """
    if target_date is None:
        target_date = date.today()

    baselines = _get_baselines(db, user_id)
    objective_values = _get_recent_objective_values(db, user_id, target_date)
    subjective_values = _get_subjective_values(db, user_id, target_date)

    result = compute_wellness_score(objective_values, subjective_values, baselines)

    # Upsert the score
    existing = (
        db.query(WellnessScore)
        .filter(
            WellnessScore.user_id == user_id,
            WellnessScore.score_date == target_date,
        )
        .first()
    )

    if existing:
        existing.score = result.score
        existing.objective_score = result.objective_score
        existing.subjective_score = result.subjective_score
        existing.contributing_factors_json = _factors_to_json(result.contributing_factors)
        existing.computed_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing

    ws = WellnessScore(
        user_id=user_id,
        score_date=target_date,
        score=result.score,
        objective_score=result.objective_score,
        subjective_score=result.subjective_score,
        contributing_factors_json=_factors_to_json(result.contributing_factors),
    )
    db.add(ws)
    db.commit()
    db.refresh(ws)

    logger.info(
        "wellness_score_computed",
        extra={
            "user_id": user_id,
            "date": str(target_date),
            "score": result.score,
            "objective": result.objective_score,
            "subjective": result.subjective_score,
        },
    )

    return ws


def get_score(db: Session, user_id: int, target_date: date) -> Optional[WellnessScore]:
    """Get a stored wellness score for a specific date."""
    return (
        db.query(WellnessScore)
        .filter(
            WellnessScore.user_id == user_id,
            WellnessScore.score_date == target_date,
        )
        .first()
    )


def get_score_history(
    db: Session,
    user_id: int,
    days: int = 30,
) -> List[WellnessScore]:
    """Get wellness score history for the last N days."""
    since = date.today() - timedelta(days=days)
    return (
        db.query(WellnessScore)
        .filter(
            WellnessScore.user_id == user_id,
            WellnessScore.score_date >= since,
        )
        .order_by(WellnessScore.score_date.desc())
        .all()
    )

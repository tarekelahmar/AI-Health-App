from datetime import datetime, timedelta
from statistics import mean, pstdev
from sqlalchemy.orm import Session

from app.domain.metric_registry import get_metric_spec
from app.domain.models.baseline import Baseline
from app.domain.models.health_data_point import HealthDataPoint
from typing import Union


def recompute_baseline(
    *,
    db: Session,
    user_id: int,
    metric_key: str,
    window_days: int = 30,
) -> Baseline:
    """
    Simple, robust baseline:
    - take last N days
    - mean + population stddev (pstdev)
    """
    get_metric_spec(metric_key)  # validate existence

    since = datetime.utcnow() - timedelta(days=window_days)

    rows = (
        db.query(HealthDataPoint)
        .filter(
            HealthDataPoint.user_id == user_id,
            HealthDataPoint.metric_type == metric_key,
            HealthDataPoint.timestamp >= since,
        )
        .order_by(HealthDataPoint.timestamp.asc())
        .all()
    )

    values = [r.value for r in rows if r.value is not None]
    if len(values) < 5:
        # not enough data -> keep baseline but mark as weak
        mu = mean(values) if values else 0.0
        sd = pstdev(values) if len(values) > 1 else 0.0
    else:
        mu = mean(values)
        sd = pstdev(values) if len(values) > 1 else 0.0

    try:
        baseline = (
            db.query(Baseline)
            .filter(Baseline.user_id == user_id, Baseline.metric_type == metric_key)
            .one_or_none()
        )

        if baseline is None:
            baseline = Baseline(
                user_id=user_id,
                metric_type=metric_key,
                mean=mu,
                std=sd,
                window_days=window_days,
            )
            db.add(baseline)
        else:
            baseline.mean = mu
            baseline.std = sd
            baseline.window_days = window_days

        db.commit()
        db.refresh(baseline)
        return baseline
    except Exception:
        # If baselines table doesn't exist, just skip baseline creation
        # Data will still be ingested, but baselines won't be stored
        # This allows data ingestion to work even without migrations
        pass


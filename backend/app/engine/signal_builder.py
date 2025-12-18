from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.domain.models.health_data_point import HealthDataPoint


def fetch_recent_values(
    *,
    db: Session,
    user_id: int,
    metric_key: str,
    window_days: int,
) -> list[float]:
    """
    Fetch recent scalar values for a metric.

    NOTE: We intentionally query only the columns we need (value and timestamp)
    instead of selecting the full HealthDataPoint entity. This keeps the query
    resilient if legacy databases are missing newer, optional columns such as
    data_provenance_id or quality_score.
    """
    since = datetime.utcnow() - timedelta(days=window_days)
    rows = (
        db.query(HealthDataPoint.value)
        .filter(
            HealthDataPoint.user_id == user_id,
            HealthDataPoint.metric_type == metric_key,
            HealthDataPoint.timestamp >= since,
        )
        .order_by(HealthDataPoint.timestamp.asc())
        .all()
    )
    # Each row is a single-column result (value,)
    return [r[0] for r in rows if r[0] is not None]



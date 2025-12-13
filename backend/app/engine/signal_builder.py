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
    return [r.value for r in rows if r.value is not None]


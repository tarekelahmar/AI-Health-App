from sqlalchemy.orm import Session
from app.domain.models.health_data_point import HealthDataPoint
from app.core.signal import Signal


class SignalRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_user(self, user_id: int) -> list[Signal]:
        rows = (
            self.db.query(HealthDataPoint)
            .filter(HealthDataPoint.user_id == user_id)
            .order_by(HealthDataPoint.timestamp.asc())
            .all()
        )

        return [
            Signal(
                user_id=user_id,
                metric_key=row.metric_type,
                value=row.value,
                unit=row.unit or "",
                timestamp=row.timestamp,
                source=row.source or "manual",
                reliability=0.5,  # Default reliability, will be set properly when using observe_signal
            )
            for row in rows
        ]


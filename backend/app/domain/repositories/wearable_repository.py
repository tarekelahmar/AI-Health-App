from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from app.domain.models.wearable_sample import WearableSample


class WearableRepository:
    """Data access for WearableSample entities."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        user_id: int,
        device_type: str,
        metric_type: str,
        value: float,
        unit: str,
        timestamp: Optional[datetime] = None,
        device_id: Optional[str] = None,
    ) -> WearableSample:
        sample = WearableSample(
            user_id=user_id,
            device_type=device_type,
            metric_type=metric_type,
            value=value,
            unit=unit,
            timestamp=timestamp or datetime.utcnow(),
            device_id=device_id or "",
        )
        self.db.add(sample)
        self.db.commit()
        self.db.refresh(sample)
        return sample

    def bulk_create(self, samples: List[dict]) -> None:
        """Efficient bulk insert for high-volume wearable streams."""
        objs = [WearableSample(**payload) for payload in samples]
        self.db.bulk_save_objects(objs)
        self.db.commit()

    def list_for_user_in_range(
        self,
        user_id: int,
        start: datetime,
        end: datetime,
        metric_type: Optional[str] = None,
    ) -> List[WearableSample]:
        q = (
            self.db.query(WearableSample)
            .filter(
                WearableSample.user_id == user_id,
                WearableSample.timestamp >= start,
                WearableSample.timestamp <= end,
            )
        )
        if metric_type:
            q = q.filter(WearableSample.metric_type == metric_type)

        return q.order_by(WearableSample.timestamp.asc()).all()

    def get_latest_value(
        self,
        user_id: int,
        metric_type: str,
    ) -> Optional[WearableSample]:
        return (
            self.db.query(WearableSample)
            .filter(
                WearableSample.user_id == user_id,
                WearableSample.metric_type == metric_type,
            )
            .order_by(WearableSample.timestamp.desc())
            .first()
        )


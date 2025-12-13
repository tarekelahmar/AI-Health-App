from sqlalchemy.orm import Session
from typing import Optional
from app.engine.baselines import Baseline
from app.domain.models.baseline import Baseline as BaselineModel


class BaselineRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, *, user_id: int, metric_key: str) -> Optional[Baseline]:
        """Get baseline - returns engine Baseline class, not model"""
        row = (
            self.db.query(BaselineModel)
            .filter(
                BaselineModel.user_id == user_id,
                BaselineModel.metric_key == metric_key,
            )
            .one_or_none()
        )
        
        if not row:
            return None
        
        # Convert model to engine Baseline class
        return Baseline(
            metric_key=row.metric_key,
            mean_value=row.mean,
            std_value=row.std,
            sample_count=row.sample_count,
            window_days=row.window_days,
        )


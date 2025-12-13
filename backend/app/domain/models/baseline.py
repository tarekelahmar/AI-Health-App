from sqlalchemy import Column, Integer, Float, String, DateTime, Index
from sqlalchemy.sql import func
from app.core.database import Base


class Baseline(Base):
    __tablename__ = "baselines"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    metric_type = Column(String, index=True, nullable=False)
    mean = Column(Float, nullable=False)
    std = Column(Float, nullable=False)
    window_days = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_baseline_user_metric", "user_id", "metric_type", unique=True),
    )

from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey
from app.core.database import Base


class ExperimentResult(Base):
    __tablename__ = "experiment_results"

    id = Column(Integer, primary_key=True)
    experiment_run_id = Column(Integer, ForeignKey("experiment_runs.id"), nullable=False)

    baseline_mean = Column(Float, nullable=False)
    followup_mean = Column(Float, nullable=False)
    delta = Column(Float, nullable=False)

    effect_size = Column(Float, nullable=True)   # Cohen's d
    confidence = Column(Float, nullable=False)   # 0..1

    conclusion = Column(String, nullable=False)  # improved / worsened / no_change
    created_at = Column(DateTime, default=datetime.utcnow)


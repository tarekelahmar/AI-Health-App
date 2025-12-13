from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from app.core.database import Base


class ExperimentRun(Base):
    __tablename__ = "experiment_runs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    intervention_id = Column(Integer, ForeignKey("interventions.id"), nullable=False)

    target_metric = Column(String, nullable=False)   # e.g. sleep_duration

    baseline_start = Column(DateTime, nullable=False)
    baseline_end = Column(DateTime, nullable=False)

    followup_start = Column(DateTime, nullable=False)
    followup_end = Column(DateTime, nullable=False)

    status = Column(String, default="running")       # running / complete
    created_at = Column(DateTime, default=datetime.utcnow)


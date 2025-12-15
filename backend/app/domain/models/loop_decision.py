from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey

from app.core.database import Base


class LoopDecision(Base):
    __tablename__ = "loop_decisions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    experiment_id = Column(Integer, ForeignKey("experiments.id"), nullable=False)
    evaluation_id = Column(Integer, ForeignKey("evaluation_results.id"), nullable=False)

    action = Column(String, nullable=False)  # continue | stop | adjust | extend
    reason = Column(String, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    metadata_json = Column(JSON, default=dict)


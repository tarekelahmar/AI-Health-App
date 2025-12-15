from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Index
from app.core.database import Base


class CausalGraphEdge(Base):
    __tablename__ = "causal_graph_edges"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)

    # "driver" can be a metric_key or an intervention_key or behavior_key
    driver_key = Column(String, index=True, nullable=False)
    driver_kind = Column(String, nullable=False)  # "metric" | "intervention" | "behavior"

    target_metric_key = Column(String, index=True, nullable=False)

    # effect summary
    lag_days = Column(Integer, nullable=False, default=0)
    direction = Column(String, nullable=False)  # "up" | "down"
    effect_size = Column(Float, nullable=False, default=0.0)  # standardized (Cohen's d-like)
    confidence = Column(Float, nullable=False, default=0.0)
    coverage = Column(Float, nullable=False, default=0.0)

    # penalties / adjustments
    confounder_penalty = Column(Float, nullable=False, default=0.0)  # subtract from score
    interaction_boost = Column(Float, nullable=False, default=0.0)   # add to score

    # final edge score (what we rank on)
    score = Column(Float, index=True, nullable=False, default=0.0)

    details_json = Column(Text, nullable=False, default="{}")
    generated_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("ix_causal_edges_user_target_score", "user_id", "target_metric_key", "score"),
    )


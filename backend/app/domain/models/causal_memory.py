from __future__ import annotations

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Index, JSON

from app.core.database import Base


class CausalMemory(Base):
    """
    Causal Memory Layer - WHY the system believes something.
    
    Tracks what works for each user over time, accumulating evidence
    from evaluations, attributions, and experiments.
    """
    __tablename__ = "causal_memory"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)

    driver_type = Column(String(50), nullable=False)  # "behavior" | "supplement" | "sleep" | "lab" | "exercise"
    driver_key = Column(String(100), nullable=False)  # e.g. "melatonin", "late_caffeine"
    metric_key = Column(String(100), nullable=False)  # e.g. "sleep_duration", "energy"

    direction = Column(String(20), nullable=False)  # "improves" | "worsens" | "mixed"
    avg_effect_size = Column(Float, nullable=False)  # Average effect size across all evidence
    confidence = Column(Float, nullable=False)  # [0-1] - confidence in this memory
    evidence_count = Column(Integer, nullable=False, default=0)  # Number of supporting evaluations/attributions

    first_seen_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_confirmed_at = Column(DateTime, nullable=True)  # When this was last confirmed by new evidence
    status = Column(String(20), nullable=False, default="tentative")  # "tentative" | "confirmed" | "deprecated"

    # Using JSON instead of JSONB for SQLite compatibility in tests
    supporting_evaluations_json = Column(JSON, nullable=True)  # List of evaluation IDs and their contributions

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_causal_memory_user_driver_metric", "user_id", "driver_key", "metric_key", unique=True),
        Index("ix_causal_memory_user_status", "user_id", "status"),
        Index("ix_causal_memory_confidence", "user_id", "confidence"),
    )


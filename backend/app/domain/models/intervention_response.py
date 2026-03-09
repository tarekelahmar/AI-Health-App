"""
Intervention Response Model - Phase 3.1

Consolidates what happened when a user tried an intervention.
Wraps one or more EvaluationResults into a single user-facing record
with subjective feedback, confounders, and verdict.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Text, JSON, Index,
)

from app.core.database import Base


class InterventionResponse(Base):
    """
    Records the complete outcome of an intervention trial.

    Links to the Intervention and Experiment that produced it,
    but stores a denormalized summary for fast querying.
    """
    __tablename__ = "intervention_responses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)

    # What was tried
    intervention_id = Column(Integer, index=True, nullable=False)
    intervention_key = Column(String(100), index=True, nullable=False)
    experiment_id = Column(Integer, nullable=True)

    # When
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)
    duration_days = Column(Integer, nullable=True)

    # Target metrics and outcomes (JSON for flexibility)
    # Shape: {"sleep_duration": {"baseline": 410, "outcome": 445, "effect_size": 0.62, "direction": "up"}, ...}
    target_metrics_json = Column(JSON, nullable=True)

    # Aggregated verdict across all metrics
    verdict = Column(String(30), nullable=False)  # helpful | not_helpful | unclear | insufficient_data
    overall_effect_size = Column(Float, nullable=True)
    overall_confidence = Column(Float, nullable=True)

    # Confounders and context
    confounders_json = Column(JSON, nullable=True)  # ["travel", "illness", "medication_change"]
    regime_during = Column(String(50), nullable=True)  # normal | illness | travel | high_stress

    # User subjective feedback
    user_perceived_benefit = Column(Integer, nullable=True)  # 1-5 scale
    user_notes = Column(Text, nullable=True)
    would_recommend = Column(Integer, nullable=True)  # 0=no, 1=yes

    # Adherence
    adherence_rate = Column(Float, nullable=True)  # 0-1

    # Linked evaluation IDs for drill-down
    evaluation_ids_json = Column(JSON, nullable=True)  # [1, 2, 3]

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_intervention_response_user_key", "user_id", "intervention_key"),
        Index("ix_intervention_response_user_verdict", "user_id", "verdict"),
    )

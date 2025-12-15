from __future__ import annotations

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Index, Boolean
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


class DecisionSignal(Base):
    """
    Governed decision signal with confidence hierarchy.
    
    Tracks the strength and reliability of insights/attributions/evaluations
    to prevent overclaiming and ensure appropriate language + actions.
    """
    __tablename__ = "decision_signals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)

    # Link to source (insight, driver, evaluation, etc.)
    source_type = Column(String(50), nullable=False)  # "insight" | "driver" | "evaluation" | "attribution"
    source_id = Column(Integer, nullable=False)  # ID of the source record

    # Confidence hierarchy level (1-5)
    level = Column(Integer, nullable=False)  # 1=Observational, 2=Correlational, 3=Attributed, 4=Evaluated, 5=Reconfirmed
    level_name = Column(String(50), nullable=False)  # "observational" | "correlational" | "attributed" | "evaluated" | "reconfirmed"

    # Confidence metrics
    confidence = Column(Float, nullable=False)  # [0-1]
    evidence_count = Column(Integer, nullable=False, default=1)  # Number of supporting evidence points
    last_confirmed_at = Column(DateTime, nullable=True)  # When this signal was last confirmed

    # Confidence explanation (why confidence is what it is)
    confidence_explanation_json = Column(JSONB, nullable=True)  # {data_coverage, adherence_rate, effect_size, consistency, confounder_risk}

    # Claim boundary enforcement
    allowed_actions = Column(JSONB, nullable=True)  # ["monitor", "suggest_experiment", "continue_protocol"]
    language_constraints = Column(JSONB, nullable=True)  # {must_use: ["associated with"], must_not_use: ["causes", "proves"]}

    # Suppression state
    is_suppressed = Column(Boolean, nullable=False, default=False)
    suppression_reason = Column(String(200), nullable=True)
    suppression_until = Column(DateTime, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_decision_signals_user_level", "user_id", "level"),
        Index("ix_decision_signals_source", "source_type", "source_id"),
        Index("ix_decision_signals_user_created", "user_id", "created_at"),
    )


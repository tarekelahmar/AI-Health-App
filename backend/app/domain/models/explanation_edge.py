from __future__ import annotations

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship

from app.core.database import Base


class ExplanationEdge(Base):
    """
    Insight Explainability Graph - TRACEABILITY
    
    Links insights, evaluations, and narratives to their source data points,
    enabling "Why am I seeing this?" drill-down.
    """
    __tablename__ = "explanation_edges"

    id = Column(Integer, primary_key=True, index=True)
    
    # Link to the insight/evaluation/narrative being explained
    target_type = Column(String(50), nullable=False)  # "insight" | "evaluation" | "narrative"
    target_id = Column(Integer, nullable=False)  # ID of the target record
    
    # Source of the explanation
    source_type = Column(String(50), nullable=False)  # "metric" | "experiment" | "evaluation" | "checkin" | "provider" | "memory"
    source_id = Column(Integer, nullable=True)  # ID of the source record (nullable for metric/provider sources)
    
    # Contribution metadata
    contribution_weight = Column(Float, nullable=False, default=1.0)  # [0-1] - how much this source contributed
    description = Column(Text, nullable=True)  # Human-readable description of the contribution
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_explanation_edges_target", "target_type", "target_id"),
        Index("ix_explanation_edges_source", "source_type", "source_id"),
    )


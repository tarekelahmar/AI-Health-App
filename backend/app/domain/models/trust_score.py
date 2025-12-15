from __future__ import annotations

from datetime import datetime
from sqlalchemy import Column, Integer, Float, DateTime, Index

from app.core.database import Base


class TrustScore(Base):
    """
    Trust Score - per user, per system
    
    Tracks system confidence in its recommendations for a user,
    based on data coverage, adherence, evaluation success, and stability.
    """
    __tablename__ = "trust_scores"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False, unique=True)

    score = Column(Float, nullable=False, default=0.0)  # [0-100] - overall trust score
    
    # Component scores
    data_coverage_score = Column(Float, nullable=False, default=0.0)  # [0-100]
    adherence_score = Column(Float, nullable=False, default=0.0)  # [0-100]
    evaluation_success_rate = Column(Float, nullable=False, default=0.0)  # [0-100] - % of evaluations with positive outcomes
    stability_score = Column(Float, nullable=False, default=0.0)  # [0-100] - consistency of patterns over time

    last_updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_trust_scores_user", "user_id", unique=True),
    )


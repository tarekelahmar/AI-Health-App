"""
WellnessScore model — stores the daily composite wellness score.

The score blends objective wearable data with subjective journal entries
into a single 0-100 number, along with contributing factor breakdowns.
"""

from datetime import datetime, date

from sqlalchemy import Column, Integer, Float, String, Date, DateTime, JSON, UniqueConstraint

from app.core.database import Base


class WellnessScore(Base):
    __tablename__ = "wellness_scores"
    __table_args__ = (
        UniqueConstraint("user_id", "score_date", name="uq_wellness_scores_user_date"),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    score_date = Column(Date, nullable=False)

    # Composite score (0-100)
    score = Column(Float, nullable=False)

    # Sub-scores for transparency
    objective_score = Column(Float, nullable=True)   # 0-100, from wearable data
    subjective_score = Column(Float, nullable=True)  # 0-100, from journal data

    # Detailed breakdown: list of {metric_key, z_score, weight, direction, label}
    contributing_factors_json = Column(JSON, default=list)

    computed_at = Column(DateTime, default=datetime.utcnow)
